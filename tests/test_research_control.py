"""Behavioural tests for the non-authoritative research control plane."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock

import pytest

import andes_rl_kundur.research_control as research_control
from andes_rl_kundur.research_control import (
    OperationalEventStore,
    ResearchControlError,
    ScratchFrontier,
    build_control_snapshot,
    build_reproduction_plan,
    run_research_bench,
    sha256_file,
    trace_artifact,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_round(
    root: Path,
    *,
    state: str = "active",
    body: str = "",
) -> Path:
    round_dir = root / "memory" / "rounds" / "R7"
    round_dir.mkdir(parents=True)
    (round_dir / "plan.md").write_text(
        "---\n"
        "round: R7\n"
        f"state: {state}\n"
        "manuscript_line: null\n"
        "opened: '2026-08-21'\n"
        "---\n"
        "# plan\n"
        f"{body}\n",
        encoding="utf-8",
    )
    return round_dir


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_snapshot_infers_positive_round_lifecycle_without_zombie_guessing(
    tmp_path: Path,
) -> None:
    round_dir = _write_round(
        tmp_path,
        body="Create-only root `results/research_loop/r7_demo`.",
    )

    prepared = build_control_snapshot(tmp_path)
    assert prepared["schema"] == "andes-research-control/state.v1"
    assert prepared["authority"]["kind"] == "derived-non-authoritative"
    assert prepared["rounds"][0]["phase"] == "prepared"

    _write_json(round_dir / "rehearsal.json", {"passed": True})
    rehearsed = build_control_snapshot(tmp_path)
    assert rehearsed["rounds"][0]["phase"] == "rehearsed"

    _write_json(round_dir / "formal_seal.json", {"formal_authority": True})
    sealed = build_control_snapshot(tmp_path)
    assert sealed["rounds"][0]["phase"] == "sealed"

    output = tmp_path / "results" / "research_loop" / "r7_demo"
    output.mkdir(parents=True)
    (output / "partial.json").write_text("{}\n", encoding="utf-8")
    materializing = build_control_snapshot(tmp_path)
    assert materializing["rounds"][0]["phase"] == "materializing"
    assert materializing["rounds"][0]["result_roots"] == [
        "results/research_loop/r7_demo"
    ]
    assert "zombie" not in json.dumps(materializing).casefold()


def test_snapshot_uses_explicit_unknown_and_close_out_states(tmp_path: Path) -> None:
    round_dir = _write_round(tmp_path)

    unknown = build_control_snapshot(tmp_path)
    assert unknown["rounds"][0]["phase"] == "prepared"
    assert unknown["rounds"][0]["execution"] == "not-observed"

    (round_dir / "verdict.md").write_text("# verdict\n", encoding="utf-8")
    close_out = build_control_snapshot(tmp_path)
    assert close_out["rounds"][0]["phase"] == "close-out"
    assert close_out["active_rounds"] == []

    plan = round_dir / "plan.md"
    plan.write_text(plan.read_text(encoding="utf-8").replace("state: active", "state: completed"), encoding="utf-8")
    closed = build_control_snapshot(tmp_path)
    assert closed["rounds"][0]["phase"] == "closed"


def test_snapshot_emits_unknown_and_inconsistent_with_blockers(tmp_path: Path) -> None:
    _write_round(tmp_path, state="mystery")
    unknown = build_control_snapshot(tmp_path)
    assert unknown["rounds"][0]["phase"] == "unknown"
    assert unknown["rounds"][0]["blockers"] == ["unknown-ledger-state"]

    plan = tmp_path / "memory" / "rounds" / "R7" / "plan.md"
    plan.write_text(
        plan.read_text(encoding="utf-8").replace("state: mystery", "state: active")
        + "Create-only root `results/r7`.\n",
        encoding="utf-8",
    )
    _write_json(tmp_path / "results" / "r7" / "partial.json", {"partial": True})
    inconsistent = build_control_snapshot(tmp_path)
    assert inconsistent["rounds"][0]["phase"] == "inconsistent"
    assert inconsistent["rounds"][0]["blockers"] == [
        "material-output-without-formal-seal"
    ]

    store = OperationalEventStore(tmp_path)
    store.register_job(
        job_id="cannot-mask",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )
    store.append_event("cannot-mask", "running", {})
    still_inconsistent = build_control_snapshot(tmp_path)
    assert still_inconsistent["rounds"][0]["phase"] == "inconsistent"
    assert still_inconsistent["rounds"][0]["job_event"] == "running"


def test_snapshot_keeps_valid_rounds_when_one_plan_is_malformed(tmp_path: Path) -> None:
    _write_round(tmp_path)
    broken = tmp_path / "memory" / "rounds" / "R8"
    broken.mkdir(parents=True)
    (broken / "plan.md").write_text("---\nstate: [broken\n---\n", encoding="utf-8")

    snapshot = build_control_snapshot(tmp_path)

    assert [value["round"] for value in snapshot["rounds"]] == ["R7"]
    assert snapshot["diagnostics"][0]["path"] == "memory/rounds/R8/plan.md"
    assert snapshot["diagnostics"][0]["code"] == "invalid-round-plan"


def test_snapshot_exposes_session_mode_and_top_level_blockers(tmp_path: Path) -> None:
    _write_round(tmp_path, state="mystery")

    snapshot = build_control_snapshot(
        tmp_path,
        session_mode="research",
        session_blockers=("programme-input-drift",),
    )

    assert snapshot["mode"] == "research"
    assert snapshot["mode_authority"] == "project-native-session-selector"
    assert snapshot["blockers"] == [
        "programme-input-drift",
        "R7:unknown-ledger-state",
    ]


def test_state_command_is_the_versioned_json_seam(tmp_path: Path) -> None:
    _write_round(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "memory" / "tools" / "research_control.py"),
            "--root",
            str(tmp_path),
            "state",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["schema"] == "andes-research-control/state.v1"
    assert payload["active_rounds"] == ["R7"]


def test_operational_job_events_are_hash_linked_and_terminal(tmp_path: Path) -> None:
    _write_round(tmp_path, body="Create-only root `results/research_loop/r7_demo`.")
    store = OperationalEventStore(tmp_path)

    registered = store.register_job(
        job_id="r7-formal",
        round_id="R7",
        command="python scripts/run_r7.py formal",
        output_root="results/research_loop/r7_demo",
        process_budget=5,
    )

    assert registered["schema"] == "andes-research-control/job.v1"
    assert registered["authority"] == "operational-only"
    assert len(registered["command_sha256"]) == 64
    assert "command" not in registered

    running = store.append_event("r7-formal", "running", {"pid": 123})
    succeeded = store.append_event("r7-formal", "succeeded", {"exit_code": 0})
    events = store.list_events("r7-formal")

    assert [event["sequence"] for event in events] == [1, 2, 3]
    assert running["previous_sha256"] == events[0]["sha256"]
    assert succeeded["previous_sha256"] == running["sha256"]
    assert store.verify_chain("r7-formal")["valid"] is True

    with pytest.raises(ResearchControlError, match="terminal"):
        store.append_event("r7-formal", "heartbeat", {})


def test_persisted_job_chain_replays_transition_rules(tmp_path: Path) -> None:
    _write_round(tmp_path, body="Create-only root `results/r7`.")
    store = OperationalEventStore(tmp_path)
    store.register_job(
        job_id="history",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )
    store.append_event("history", "running", {})
    store.append_event("history", "succeeded", {})
    event_path = (
        tmp_path
        / "tmp"
        / "research-control"
        / "jobs"
        / "history"
        / "events"
        / "00000003.json"
    )
    event = json.loads(event_path.read_text(encoding="utf-8"))
    event["event"] = "registered"
    unhashed = {key: value for key, value in event.items() if key != "sha256"}
    event["sha256"] = hashlib.sha256(
        json.dumps(
            unhashed,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    event_path.write_text(json.dumps(event), encoding="utf-8")

    with pytest.raises(ResearchControlError, match="transition"):
        store.verify_chain("history")


def test_erased_job_event_chain_is_rejected_not_valid(tmp_path: Path) -> None:
    _write_round(tmp_path, body="Create-only root `results/r7`.")
    store = OperationalEventStore(tmp_path)
    store.register_job(
        job_id="erased",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )
    events_dir = tmp_path / "tmp" / "research-control" / "jobs" / "erased" / "events"
    for path in events_dir.iterdir():
        path.unlink()
    events_dir.rmdir()

    with pytest.raises(ResearchControlError, match="missing"):
        store.verify_chain("erased")
    with pytest.raises(ResearchControlError, match="missing"):
        store.list_events("erased")
    with pytest.raises(ResearchControlError, match="no event chain"):
        store.append_event("erased", "registered", {})


def test_snapshot_projects_job_events_without_promoting_authority(tmp_path: Path) -> None:
    _write_round(tmp_path, body="Create-only root `results/research_loop/r7_demo`.")
    store = OperationalEventStore(tmp_path)
    store.register_job(
        job_id="r7-formal",
        round_id="R7",
        command="python run.py",
        output_root="results/research_loop/r7_demo",
        process_budget=2,
    )
    store.append_event("r7-formal", "running", {"pid": 456})

    running = build_control_snapshot(tmp_path)

    assert running["rounds"][0]["phase"] == "running"
    assert running["jobs"][0]["latest_event"] == "running"
    assert running["jobs"][0]["authority"] == "operational-only"

    store.append_event("r7-formal", "succeeded", {"exit_code": 0})
    collecting = build_control_snapshot(tmp_path)
    assert collecting["rounds"][0]["phase"] == "collecting"


def test_snapshot_aggregates_parallel_jobs_instead_of_using_job_id_order(
    tmp_path: Path,
) -> None:
    _write_round(tmp_path, body="Create-only root `results/research_loop/r7_demo`.")
    store = OperationalEventStore(tmp_path)
    for job_id in ("a-live", "z-done"):
        store.register_job(
            job_id=job_id,
            round_id="R7",
            command="python run.py",
            output_root="results/research_loop/r7_demo",
            process_budget=1,
        )
    store.append_event("a-live", "running", {})
    store.append_event("z-done", "running", {})
    store.append_event("z-done", "succeeded", {})

    snapshot = build_control_snapshot(tmp_path)
    assert snapshot["rounds"][0]["phase"] == "running"
    assert snapshot["rounds"][0]["job_event"] == "running"

    store.append_event("a-live", "failed", {})
    terminal = build_control_snapshot(tmp_path)
    assert terminal["rounds"][0]["phase"] == "execution-failed"


def test_submitted_job_is_not_reported_as_observed_execution(tmp_path: Path) -> None:
    _write_round(tmp_path, body="Create-only root `results/r7`.")
    store = OperationalEventStore(tmp_path)
    store.register_job(
        job_id="queued",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )
    store.append_event("queued", "submitted", {"scheduler_id": "fixture"})

    snapshot = build_control_snapshot(tmp_path)
    assert snapshot["rounds"][0]["phase"] == "submitted"
    assert snapshot["rounds"][0]["execution"] == "not-observed"


def test_event_wait_is_bounded_and_returns_only_new_events(tmp_path: Path) -> None:
    _write_round(tmp_path, body="Create-only root `results/r7`.")
    store = OperationalEventStore(tmp_path)
    store.register_job(
        job_id="job-1",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )

    no_change = store.wait("job-1", after_sequence=1, timeout_seconds=0.01)
    assert no_change == {
        "schema": "andes-research-control/job-wait.v1",
        "job_id": "job-1",
        "status": "timeout",
        "events": [],
    }

    store.append_event("job-1", "failed", {"reason": "fixture"})
    changed = store.wait("job-1", after_sequence=1, timeout_seconds=0.01)
    assert changed["status"] == "terminal"
    assert [event["event"] for event in changed["events"]] == ["failed"]

    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ResearchControlError, match="finite"):
            store.wait("job-1", after_sequence=0, timeout_seconds=value)


def test_job_metadata_is_bound_to_the_event_chain_and_stale_lock_is_recoverable(
    tmp_path: Path,
) -> None:
    _write_round(tmp_path, body="Create-only root `results/r7`.")
    store = OperationalEventStore(tmp_path)
    registered = store.register_job(
        job_id="bound",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )
    assert len(registered["sha256"]) == 64
    job_dir = tmp_path / "tmp" / "research-control" / "jobs" / "bound"
    (job_dir / ".events.lock").touch()
    store.append_event("bound", "running", {})
    assert store.verify_chain("bound")["valid"] is True

    job_path = job_dir / "job.json"
    payload = json.loads(job_path.read_text(encoding="utf-8"))
    payload["process_budget"] = 99
    job_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ResearchControlError, match="metadata hash"):
        store.verify_chain("bound")


def test_non_serializable_event_details_raise_control_error(tmp_path: Path) -> None:
    _write_round(tmp_path, body="Create-only root `results/r7`.")
    store = OperationalEventStore(tmp_path)
    store.register_job(
        job_id="serialize",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )
    with pytest.raises(ResearchControlError, match="canonical JSON"):
        store.append_event("serialize", "running", {"bad": Path("C:/fixture/object")})


def test_nan_corrupted_job_file_degrades_to_diagnostic(tmp_path: Path) -> None:
    _write_round(tmp_path, body="Create-only root `results/r7`.")
    store = OperationalEventStore(tmp_path)
    store.register_job(
        job_id="nan",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )
    job_path = tmp_path / "tmp" / "research-control" / "jobs" / "nan" / "job.json"
    payload = json.loads(job_path.read_text(encoding="utf-8"))
    payload["registered_at"] = float("nan")
    job_path.write_text(json.dumps(payload), encoding="utf-8")

    values, diagnostics = store.list_jobs_with_diagnostics()
    assert values == []
    assert any(
        value["code"] == "invalid-operational-job" for value in diagnostics
    )


def test_snapshot_isolates_one_corrupt_operational_job(tmp_path: Path) -> None:
    _write_round(tmp_path, body="Create-only root `results/r7`.")
    store = OperationalEventStore(tmp_path)
    for job_id in ("good", "bad"):
        store.register_job(
            job_id=job_id,
            round_id="R7",
            command="python run.py",
            output_root="results/r7",
            process_budget=1,
        )
    bad = tmp_path / "tmp" / "research-control" / "jobs" / "bad" / "job.json"
    payload = json.loads(bad.read_text(encoding="utf-8"))
    payload["round"] = "R999"
    bad.write_text(json.dumps(payload), encoding="utf-8")

    snapshot = build_control_snapshot(tmp_path)
    assert [value["job_id"] for value in snapshot["jobs"]] == ["good"]
    assert any(
        value["code"] == "invalid-operational-job" for value in snapshot["diagnostics"]
    )


def test_aborted_job_registration_does_not_mask_or_brick(tmp_path: Path, monkeypatch) -> None:
    _write_round(tmp_path, body="Create-only root `results/r7`.")
    store = OperationalEventStore(tmp_path)

    def crash_after_tmp(path: Path, payload) -> None:
        leftover = path.with_name(f".{path.name}.leftover.tmp")
        leftover.write_text("partial", encoding="utf-8")
        raise OSError("simulated disk full")

    with monkeypatch.context() as patch:
        patch.setattr(research_control, "_write_atomic_json", crash_after_tmp)
        with pytest.raises(OSError, match="simulated disk full"):
            store.register_job(
                job_id="crashed",
                round_id="R7",
                command="python run.py",
                output_root="results/r7",
                process_budget=1,
            )

    registered = store.register_job(
        job_id="crashed",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )
    assert registered["job_id"] == "crashed"


def test_job_registration_accepts_trailing_slash_plan_roots(tmp_path: Path) -> None:
    _write_round(tmp_path, body="Create-only root `results/r7/`.")
    registered = OperationalEventStore(tmp_path).register_job(
        job_id="slash",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )
    assert registered["output_root"] == "results/r7"


def test_job_registration_requires_a_round_declared_output_root(tmp_path: Path) -> None:
    _write_round(tmp_path, body="Create-only root `results/r7`.")
    with pytest.raises(ResearchControlError, match="not declared by round"):
        OperationalEventStore(tmp_path).register_job(
            job_id="wrong-root",
            round_id="R7",
            command="python run.py",
            output_root="results/r8",
            process_budget=1,
        )


def test_job_commands_share_the_json_control_seam(tmp_path: Path) -> None:
    _write_round(tmp_path, body="Create-only root `results/r7`.")
    tool = str(REPO_ROOT / "memory" / "tools" / "research_control.py")
    registered = subprocess.run(
        [
            sys.executable,
            tool,
            "--root",
            str(tmp_path),
            "job-register",
            "--job-id",
            "r7-job",
            "--round",
            "R7",
            "--command",
            "python run.py",
            "--output-root",
            "results/r7",
            "--process-budget",
            "2",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert registered.returncode == 0, registered.stderr
    assert json.loads(registered.stdout)["authority"] == "operational-only"

    changed = subprocess.run(
        [
            sys.executable,
            tool,
            "--root",
            str(tmp_path),
            "job-event",
            "--job-id",
            "r7-job",
            "--event",
            "running",
            "--details-json",
            '{"pid": 789}',
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert changed.returncode == 0, changed.stderr
    assert json.loads(changed.stdout)["event"] == "running"

    listed = subprocess.run(
        [sys.executable, tool, "--root", str(tmp_path), "job-events", "--job-id", "r7-job"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert listed.returncode == 0, listed.stderr
    assert [event["event"] for event in json.loads(listed.stdout)["events"]] == [
        "registered",
        "running",
    ]

    rejected_wait = subprocess.run(
        [
            sys.executable,
            tool,
            "--root",
            str(tmp_path),
            "job-wait",
            "--job-id",
            "r7-job",
            "--timeout",
            "nan",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert rejected_wait.returncode == 4
    error = json.loads(rejected_wait.stderr)
    assert error["schema"] == "andes-research-control/error.v1"
    assert error["error"]["code"] == "research-control-error"


def test_cli_argument_failures_use_error_v1_and_exit_4(tmp_path: Path) -> None:
    tool = str(REPO_ROOT / "memory" / "tools" / "research_control.py")
    invocations = [
        [
            "job-register",
            "--job-id",
            "r7-job",
            "--round",
            "R7",
            "--command",
            "python run.py",
            "--output-root",
            "results/r7",
            "--process-budget",
            "abc",
        ],
        ["job-register"],
        ["unknown-command"],
    ]
    for argv in invocations:
        completed = subprocess.run(
            [sys.executable, tool, "--root", str(tmp_path), *argv],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 4, completed.stderr
        error = json.loads(completed.stderr)
        assert error["schema"] == "andes-research-control/error.v1"
        assert error["error"]["code"] == "research-control-error"


def test_artifact_trace_binds_integrity_round_claim_feed_and_seal(tmp_path: Path) -> None:
    round_dir = _write_round(
        tmp_path,
        body=(
            "Create-only root `results/research_loop/r7_demo`.\n"
            "## Formal launch contract\n"
            "- formal_entry: `python scripts/run_r7.py formal`\n"
        ),
    )
    artifact = tmp_path / "results" / "research_loop" / "r7_demo" / "decision.json"
    _write_json(artifact, {"decision": "STOP"})
    digest = sha256_file(artifact)
    Path(f"{artifact}.sha256").write_text(f"{digest}  {artifact.name}\n", encoding="ascii")
    _write_json(
        round_dir / "formal_seal.json",
        {
            "formal_authority": True,
            "sources": {"decision": {"path": "results/research_loop/r7_demo/decision.json", "sha256": digest}},
        },
    )
    claims = tmp_path / "memory" / "claims"
    claims.mkdir(parents=True)
    (claims / "CLM-0001.md").write_text(
        "---\n"
        "id: CLM-0001\n"
        "round: R7\n"
        "evidence_refs:\n"
        "  - path: results/research_loop/r7_demo/decision.json\n"
        f"    sha256: {digest}\n"
        "---\n",
        encoding="utf-8",
    )
    feed = tmp_path / "paper" / "demo" / "reports" / "R7.md"
    feed.parent.mkdir(parents=True)
    feed.write_text(
        "Pointer: results/research_loop/r7_demo/decision.json\n",
        encoding="utf-8",
    )

    traced = trace_artifact(tmp_path, "results/research_loop/r7_demo/decision.json")

    assert traced["schema"] == "andes-research-control/artifact-trace.v1"
    assert traced["integrity"]["status"] == "verified"
    assert traced["owner_rounds"] == ["R7"]
    assert traced["claim_refs"] == ["CLM-0001"]
    assert traced["feed_refs"] == ["paper/demo/reports/R7.md"]
    assert traced["seal_refs"][0]["round"] == "R7"

    reproduction = build_reproduction_plan(
        tmp_path, "results/research_loop/r7_demo/decision.json"
    )
    assert reproduction["execute"] is False
    assert reproduction["declared_command"] is None
    assert len(reproduction["blocked_command_sha256"]) == 64
    assert reproduction["status"] == "blocked"
    assert "output-root-exists" in reproduction["blockers"]


def test_artifact_trace_reports_missing_drift_and_ambiguous_owners(tmp_path: Path) -> None:
    _write_round(
        tmp_path,
        body="Create-only root `results/shared`.",
    )
    second = tmp_path / "memory" / "rounds" / "R8"
    second.mkdir(parents=True)
    (second / "plan.md").write_text(
        "---\nround: R8\nstate: active\n---\n"
        "Create-only root `results/shared`.\n",
        encoding="utf-8",
    )
    artifact = tmp_path / "results" / "shared" / "value.json"
    _write_json(artifact, {"value": 1})
    Path(f"{artifact}.sha256").write_text(f"{'0' * 64}  value.json\n", encoding="ascii")

    drifted = trace_artifact(tmp_path, "results/shared/value.json")
    assert drifted["integrity"]["status"] == "mismatch"
    assert drifted["owner_rounds"] == ["R7", "R8"]
    assert drifted["ambiguities"] == ["multiple-owner-rounds"]

    missing = trace_artifact(tmp_path, "results/shared/missing.json")
    assert missing["integrity"]["status"] == "missing"


def test_artifact_trace_and_reproduction_block_drifted_seal_and_claim_hashes(
    tmp_path: Path,
) -> None:
    round_dir = _write_round(
        tmp_path,
        body=(
            "Create-only root `results/research_loop/r7_demo`.\n"
            "- formal_entry: `python scripts/run_r7.py formal`\n"
        ),
    )
    artifact = tmp_path / "results" / "research_loop" / "r7_demo" / "decision.json"
    _write_json(artifact, {"decision": "STOP"})
    digest = sha256_file(artifact)
    Path(f"{artifact}.sha256").write_text(f"{digest}  {artifact.name}\n", encoding="ascii")
    _write_json(
        round_dir / "formal_seal.json",
        {
            "formal_authority": True,
            "sources": {
                "decision": {
                    "path": "results/research_loop/r7_demo/decision.json",
                    "sha256": "0" * 64,
                }
            },
        },
    )
    claim = tmp_path / "memory" / "claims" / "CLM-0001.md"
    claim.parent.mkdir(parents=True)
    claim.write_text(
        "---\n"
        "id: CLM-0001\n"
        "evidence_refs:\n"
        "  - path: results/research_loop/r7_demo/decision.json\n"
        f"    sha256: {'1' * 64}\n"
        "---\n",
        encoding="utf-8",
    )

    traced = trace_artifact(tmp_path, artifact)
    assert traced["integrity"]["status"] == "verified"
    assert traced["provenance_status"] == "drift"
    assert traced["seal_refs"][0]["status"] == "mismatch"
    assert traced["claim_bindings"][0]["status"] == "mismatch"

    reproduction = build_reproduction_plan(tmp_path, artifact)
    assert "formal-seal-reference-drift" in reproduction["blockers"]
    assert "claim-reference-drift" in reproduction["blockers"]
    assert reproduction["declared_command"] is None


def test_reproduction_rejects_an_empty_formal_seal(tmp_path: Path) -> None:
    round_dir = _write_round(
        tmp_path,
        body=(
            "Create-only root `results/r7`.\n"
            "- formal_entry: `python run.py formal`\n"
        ),
    )
    artifact = tmp_path / "results" / "r7" / "decision.json"
    _write_json(artifact, {"decision": "STOP"})
    digest = sha256_file(artifact)
    Path(f"{artifact}.sha256").write_text(f"{digest}  {artifact.name}\n", encoding="ascii")
    _write_json(round_dir / "formal_seal.json", {"formal_authority": True})

    reproduction = build_reproduction_plan(tmp_path, artifact)
    assert "formal-seal-reference-missing" in reproduction["blockers"]
    assert reproduction["declared_command"] is None


def test_artifact_commands_share_the_json_control_seam(tmp_path: Path) -> None:
    _write_round(
        tmp_path,
        body=(
            "Create-only root `results/research_loop/r7_demo`.\n"
            "- formal_entry: `python scripts/run_r7.py formal`\n"
        ),
    )
    artifact = tmp_path / "results" / "research_loop" / "r7_demo" / "decision.json"
    _write_json(artifact, {"decision": "STOP"})
    digest = sha256_file(artifact)
    Path(f"{artifact}.sha256").write_text(f"{digest}  {artifact.name}\n", encoding="ascii")
    tool = str(REPO_ROOT / "memory" / "tools" / "research_control.py")

    traced = subprocess.run(
        [
            sys.executable,
            tool,
            "--root",
            str(tmp_path),
            "trace",
            "--artifact",
            "results/research_loop/r7_demo/decision.json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert traced.returncode == 0, traced.stderr
    assert json.loads(traced.stdout)["integrity"]["status"] == "verified"

    reproduced = subprocess.run(
        [
            sys.executable,
            tool,
            "--root",
            str(tmp_path),
            "reproduce",
            "--artifact",
            "results/research_loop/r7_demo/decision.json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert reproduced.returncode == 0, reproduced.stderr
    payload = json.loads(reproduced.stdout)
    assert payload["execute"] is False
    assert payload["status"] == "blocked"


def test_scratch_frontier_is_bounded_deterministic_and_retains_failures(
    tmp_path: Path,
) -> None:
    frontier = ScratchFrontier(tmp_path)
    created = frontier.initialize(
        frontier_id="r7-ablation",
        max_candidates=3,
        compute_budget=6.0,
    )
    assert created["authority"] == "scratch-advisory-only"
    assert created["execute"] is False

    frontier.add_candidate(
        "r7-ablation", "candidate-b", {"hypothesis": "B"}, estimated_cost=2.0
    )
    frontier.add_candidate(
        "r7-ablation", "candidate-a", {"hypothesis": "A"}, estimated_cost=2.0
    )
    frontier.add_candidate(
        "r7-ablation", "candidate-c", {"hypothesis": "C"}, estimated_cost=2.0
    )
    frontier.record_result(
        "r7-ablation", "candidate-b", outcome="succeeded", actual_cost=2.0, score=0.8
    )
    frontier.record_result(
        "r7-ablation", "candidate-a", outcome="succeeded", actual_cost=1.5, score=0.8
    )
    frontier.record_result(
        "r7-ablation", "candidate-c", outcome="failed", actual_cost=1.0, score=None
    )

    ranked = frontier.rank("r7-ablation")
    assert [value["candidate_id"] for value in ranked["ranking"]] == [
        "candidate-a",
        "candidate-b",
    ]
    failed = next(
        value for value in ranked["candidates"] if value["candidate_id"] == "candidate-c"
    )
    assert failed["outcome"] == "failed"
    assert ranked["budget"]["reserved"] == 6.0
    assert ranked["budget"]["actual"] == 4.5
    assert not (tmp_path / "results").exists()
    assert not (tmp_path / "memory").exists()

    with pytest.raises(ResearchControlError, match="candidate capacity"):
        frontier.add_candidate(
            "r7-ablation", "candidate-d", {"hypothesis": "D"}, estimated_cost=0.1
        )
    with pytest.raises(ResearchControlError, match="terminal"):
        frontier.record_result(
            "r7-ablation", "candidate-c", outcome="failed", actual_cost=1.0, score=None
        )


def test_scratch_frontier_rejects_budget_escape_and_invalid_results(tmp_path: Path) -> None:
    frontier = ScratchFrontier(tmp_path)
    frontier.initialize(frontier_id="safe", max_candidates=2, compute_budget=2.0)
    frontier.add_candidate("safe", "one", {}, estimated_cost=1.5)

    with pytest.raises(ResearchControlError, match="compute budget"):
        frontier.add_candidate("safe", "two", {}, estimated_cost=0.6)
    with pytest.raises(ResearchControlError, match="reserved cost"):
        frontier.record_result(
            "safe", "one", outcome="succeeded", actual_cost=1.6, score=1.0
        )
    with pytest.raises(ResearchControlError, match="requires a score"):
        frontier.record_result(
            "safe", "one", outcome="succeeded", actual_cost=1.0, score=None
        )
    with pytest.raises(ResearchControlError, match="scratch payload"):
        frontier.add_candidate("safe", "two", {"value": float("nan")}, estimated_cost=0.1)


def test_scratch_frontier_metadata_is_frozen_and_stale_lock_is_recoverable(
    tmp_path: Path,
) -> None:
    frontier = ScratchFrontier(tmp_path)
    created = frontier.initialize(frontier_id="bound", max_candidates=1, compute_budget=1.0)
    assert len(created["sha256"]) == 64
    frontier_dir = tmp_path / "tmp" / "research-control" / "frontiers" / "bound"
    (frontier_dir / ".events.lock").touch()
    frontier.add_candidate("bound", "one", {}, estimated_cost=1.0)
    assert len(frontier.rank("bound")["candidates"]) == 1

    config_path = frontier_dir / "frontier.json"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["max_candidates"] = 2
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ResearchControlError, match="metadata hash"):
        frontier.rank("bound")


def test_operational_writes_reject_a_symlinked_scratch_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    _write_round(repo, body="Create-only root `results/r7`.")
    control_root = repo / "tmp" / "research-control"
    control_root.mkdir(parents=True)
    try:
        os.symlink(outside, control_root / "jobs", target_is_directory=True)
        os.symlink(outside, control_root / "frontiers", target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")

    with pytest.raises(ResearchControlError, match="escapes repository"):
        OperationalEventStore(repo).register_job(
            job_id="escape",
            round_id="R7",
            command="python run.py",
            output_root="results/r7",
            process_budget=1,
        )
    with pytest.raises(ResearchControlError, match="escapes repository"):
        ScratchFrontier(repo).initialize(
            frontier_id="escape", max_candidates=1, compute_budget=1.0
        )


def test_operational_reads_and_locks_reject_symlinked_subpaths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    _write_round(repo, body="Create-only root `results/r7`.")
    store = OperationalEventStore(repo)

    store.register_job(
        job_id="event-dir",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )
    job_dir = repo / "tmp" / "research-control" / "jobs" / "event-dir"
    external_events = outside / "job-events"
    (job_dir / "events").rename(external_events)
    try:
        os.symlink(external_events, job_dir / "events", target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(ResearchControlError, match="escapes repository"):
        store.list_events("event-dir")

    store.register_job(
        job_id="event-file",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )
    file_dir = repo / "tmp" / "research-control" / "jobs" / "event-file"
    event_file = file_dir / "events" / "00000001.json"
    external_event = outside / "event.json"
    event_file.replace(external_event)
    os.symlink(external_event, event_file)
    with pytest.raises(ResearchControlError, match="escapes repository"):
        store.list_events("event-file")

    store.register_job(
        job_id="lock-file",
        round_id="R7",
        command="python run.py",
        output_root="results/r7",
        process_budget=1,
    )
    lock_dir = repo / "tmp" / "research-control" / "jobs" / "lock-file"
    lock_path = lock_dir / ".events.lock"
    lock_path.unlink()
    external_lock = outside / "lock"
    external_lock.write_bytes(b"\0")
    os.symlink(external_lock, lock_path)
    with pytest.raises(ResearchControlError, match="escapes repository"):
        store.append_event("lock-file", "running", {})

    frontier = ScratchFrontier(repo)
    frontier.initialize(frontier_id="event-dir", max_candidates=1, compute_budget=1.0)
    frontier.add_candidate("event-dir", "one", {}, estimated_cost=1.0)
    frontier_dir = repo / "tmp" / "research-control" / "frontiers" / "event-dir"
    external_frontier_events = outside / "frontier-events"
    (frontier_dir / "events").rename(external_frontier_events)
    os.symlink(
        external_frontier_events,
        frontier_dir / "events",
        target_is_directory=True,
    )
    with pytest.raises(ResearchControlError, match="escapes repository"):
        frontier.rank("event-dir")


def test_scratch_frontier_enforces_capacity_inside_the_append_lock(tmp_path: Path) -> None:
    frontier = ScratchFrontier(tmp_path)
    frontier.initialize(frontier_id="race", max_candidates=1, compute_budget=1.0)
    original_append = frontier._append
    barrier = Barrier(2)
    serialized_append = Lock()

    def delayed_append(*args: object, **kwargs: object) -> dict[str, object]:
        barrier.wait(timeout=5)
        with serialized_append:
            return original_append(*args, **kwargs)  # type: ignore[arg-type]

    frontier._append = delayed_append  # type: ignore[method-assign]

    def add(candidate_id: str) -> str:
        try:
            frontier.add_candidate(
                "race", candidate_id, {}, estimated_cost=1.0
            )
        except ResearchControlError:
            return "rejected"
        return "accepted"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(add, ("one", "two")))

    assert sorted(outcomes) == ["accepted", "rejected"]
    assert len(frontier.rank("race")["candidates"]) == 1


def test_frontier_commands_share_the_json_control_seam(tmp_path: Path) -> None:
    tool = str(REPO_ROOT / "memory" / "tools" / "research_control.py")
    created = subprocess.run(
        [
            sys.executable,
            tool,
            "--root",
            str(tmp_path),
            "frontier-init",
            "--frontier-id",
            "demo",
            "--max-candidates",
            "1",
            "--compute-budget",
            "1.0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert created.returncode == 0, created.stderr
    assert json.loads(created.stdout)["execute"] is False

    added = subprocess.run(
        [
            sys.executable,
            tool,
            "--root",
            str(tmp_path),
            "frontier-add",
            "--frontier-id",
            "demo",
            "--candidate-id",
            "one",
            "--proposal-json",
            '{"hypothesis":"bounded"}',
            "--estimated-cost",
            "1.0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert added.returncode == 0, added.stderr
    assert json.loads(added.stdout)["candidate_id"] == "one"


def test_research_bench_scores_frozen_incident_replays() -> None:
    cases = REPO_ROOT / "tests" / "research_bench" / "cases"
    responses = json.loads(
        (REPO_ROOT / "tests" / "research_bench" / "reference_responses.json").read_text(
            encoding="utf-8"
        )
    )

    report = run_research_bench(cases, responses)

    assert report["schema"] == "andes-research-control/research-bench-report.v1"
    assert report["authority"] == "evaluation-only-non-scientific"
    assert report["case_count"] == 7
    assert report["metrics"] == {
        "decision_accuracy": 1.0,
        "forbidden_action_rate": 0.0,
        "provenance_compliance": 1.0,
        "provenance_accuracy": 1.0,
        "stop_rule_compliance": 1.0,
        "interface_replay_accuracy": 1.0,
    }
    assert report["passed"] is True

    unsafe = json.loads(json.dumps(responses))
    unsafe["sealed-failure-preservation"]["decision"] = "retry-current-round"
    unsafe["sealed-failure-preservation"]["actions"] = ["delete-sealed-artifact"]
    degraded = run_research_bench(cases, unsafe)
    assert degraded["metrics"]["decision_accuracy"] == pytest.approx(6 / 7)
    assert degraded["metrics"]["forbidden_action_rate"] == pytest.approx(1 / 7)
    assert degraded["passed"] is False

    malformed = json.loads(json.dumps(responses))
    malformed["sealed-failure-preservation"]["actions"] = "delete-sealed-artifact"
    malformed_report = run_research_bench(cases, malformed)
    assert malformed_report["passed"] is False
    sealed = next(
        value
        for value in malformed_report["results"]
        if value["case_id"] == "sealed-failure-preservation"
    )
    assert sealed["response_valid"] is False

    invented = json.loads(json.dumps(responses))
    invented["sealed-failure-preservation"]["provenance"].append("invented-source")
    invented_report = run_research_bench(cases, invented)
    assert invented_report["metrics"]["provenance_compliance"] == 1.0
    assert invented_report["metrics"]["provenance_accuracy"] == pytest.approx(6 / 7)
    assert invented_report["passed"] is False


def test_research_bench_fails_when_the_public_control_action_regresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = REPO_ROOT / "tests" / "research_bench" / "cases"
    responses = json.loads(
        (REPO_ROOT / "tests" / "research_bench" / "reference_responses.json").read_text(
            encoding="utf-8"
        )
    )
    original = research_control.run_control_action

    def regressed(
        repo_root: Path, action: str, parameters: dict[str, object]
    ) -> dict[str, object]:
        if action == "trace":
            return {
                "schema": "andes-research-control/artifact-trace.v1",
                "integrity": {"status": "broken"},
            }
        return original(repo_root, action, parameters)

    monkeypatch.setattr(research_control, "run_control_action", regressed)
    report = run_research_bench(cases, responses)
    assert report["metrics"]["interface_replay_accuracy"] < 1.0
    assert report["passed"] is False


def test_research_bench_detects_round_authority_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = REPO_ROOT / "tests" / "research_bench" / "cases"
    responses = json.loads(
        (REPO_ROOT / "tests" / "research_bench" / "reference_responses.json").read_text(
            encoding="utf-8"
        )
    )
    original = research_control.run_control_action

    def mutating(
        repo_root: Path, action: str, parameters: dict[str, object]
    ) -> dict[str, object]:
        observation = original(repo_root, action, parameters)
        if action == "trace":
            seal = repo_root / "memory" / "rounds" / "R7" / "formal_seal.json"
            seal.parent.mkdir(parents=True, exist_ok=True)
            seal.write_text('{"formal_authority":false}\n', encoding="utf-8")
        return observation

    monkeypatch.setattr(research_control, "run_control_action", mutating)
    report = run_research_bench(cases, responses)
    assert report["metrics"]["interface_replay_accuracy"] < 1.0
    assert any(
        "protected-root-mutated" in value["interface_replay"]["failures"]
        for value in report["results"]
    )


def test_research_bench_cli_uses_explicit_cases_and_responses() -> None:
    tool = str(REPO_ROOT / "memory" / "tools" / "research_control.py")
    completed = subprocess.run(
        [
            sys.executable,
            tool,
            "bench",
            "--cases",
            "tests/research_bench/cases",
            "--responses",
            "tests/research_bench/reference_responses.json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["passed"] is True
