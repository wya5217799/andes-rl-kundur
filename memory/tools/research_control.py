"""Operate the repository's non-authoritative research control plane.

This command emits versioned JSON.  It does not reserve rounds, authorize
scientific execution, register claims, or edit sealed evidence.

Usage::

    python memory/tools/research_control.py state
    python memory/tools/research_control.py --root C:\\repo state
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from andes_rl_kundur.research_control import (  # noqa: E402
    OperationalEventStore,
    ResearchControlError,
    ScratchFrontier,
    build_control_snapshot,
    build_reproduction_plan,
    run_research_bench,
    trace_artifact,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    subcommands = parser.add_subparsers(dest="action", required=True)
    subcommands.add_parser("state", help="emit the derived research lifecycle snapshot")
    register = subcommands.add_parser(
        "job-register", help="register one operational-only long job"
    )
    register.add_argument("--job-id", required=True)
    register.add_argument("--round", dest="round_id", required=True)
    register.add_argument("--command", dest="job_command", required=True)
    register.add_argument("--output-root", required=True)
    register.add_argument("--process-budget", required=True, type=int)
    event = subcommands.add_parser("job-event", help="append one operational job event")
    event.add_argument("--job-id", required=True)
    event.add_argument("--event", required=True)
    event.add_argument("--details-json", default="{}")
    events = subcommands.add_parser("job-events", help="list verified job events")
    events.add_argument("--job-id", required=True)
    verify = subcommands.add_parser("job-verify", help="verify one event hash chain")
    verify.add_argument("--job-id", required=True)
    wait = subcommands.add_parser("job-wait", help="wait briefly for a new job event")
    wait.add_argument("--job-id", required=True)
    wait.add_argument("--after", type=int, default=0)
    wait.add_argument("--timeout", type=float, default=30.0)
    trace = subcommands.add_parser(
        "trace", help="trace one artifact through integrity and evidence records"
    )
    trace.add_argument("--artifact", required=True)
    reproduce = subcommands.add_parser(
        "reproduce", help="emit a non-executing safe reproduction plan"
    )
    reproduce.add_argument("--artifact", required=True)
    frontier_init = subcommands.add_parser(
        "frontier-init", help="freeze a finite scratch-only candidate envelope"
    )
    frontier_init.add_argument("--frontier-id", required=True)
    frontier_init.add_argument("--max-candidates", required=True, type=int)
    frontier_init.add_argument("--compute-budget", required=True, type=float)
    frontier_add = subcommands.add_parser(
        "frontier-add", help="reserve one candidate inside a scratch frontier"
    )
    frontier_add.add_argument("--frontier-id", required=True)
    frontier_add.add_argument("--candidate-id", required=True)
    frontier_add.add_argument("--proposal-json", default="{}")
    frontier_add.add_argument("--estimated-cost", required=True, type=float)
    frontier_record = subcommands.add_parser(
        "frontier-record", help="append one terminal scratch candidate result"
    )
    frontier_record.add_argument("--frontier-id", required=True)
    frontier_record.add_argument("--candidate-id", required=True)
    frontier_record.add_argument(
        "--outcome", required=True, choices=("succeeded", "failed", "rejected")
    )
    frontier_record.add_argument("--actual-cost", required=True, type=float)
    frontier_record.add_argument("--score", type=float)
    frontier_rank = subcommands.add_parser(
        "frontier-rank", help="rank successful scratch candidates deterministically"
    )
    frontier_rank.add_argument("--frontier-id", required=True)
    bench = subcommands.add_parser(
        "bench", help="score responses against frozen research incident cases"
    )
    bench.add_argument("--cases", required=True, type=Path)
    bench.add_argument("--responses", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        store = OperationalEventStore(args.root)
        frontier = ScratchFrontier(args.root)
        if args.action == "state":
            payload = build_control_snapshot(args.root)
        elif args.action == "job-register":
            payload = store.register_job(
                job_id=args.job_id,
                round_id=args.round_id,
                command=args.job_command,
                output_root=args.output_root,
                process_budget=args.process_budget,
            )
        elif args.action == "job-event":
            details = json.loads(args.details_json)
            if not isinstance(details, dict):
                raise ResearchControlError("event details must be a JSON object")
            payload = store.append_event(args.job_id, args.event, details)
        elif args.action == "job-events":
            payload = {
                "schema": "andes-research-control/events.v1",
                "job_id": args.job_id,
                "events": store.list_events(args.job_id),
            }
        elif args.action == "job-verify":
            payload = store.verify_chain(args.job_id)
        elif args.action == "job-wait":
            payload = store.wait(
                args.job_id,
                after_sequence=args.after,
                timeout_seconds=args.timeout,
            )
        elif args.action == "trace":
            payload = trace_artifact(args.root, args.artifact)
        elif args.action == "reproduce":
            payload = build_reproduction_plan(args.root, args.artifact)
        elif args.action == "frontier-init":
            payload = frontier.initialize(
                frontier_id=args.frontier_id,
                max_candidates=args.max_candidates,
                compute_budget=args.compute_budget,
            )
        elif args.action == "frontier-add":
            proposal = json.loads(args.proposal_json)
            if not isinstance(proposal, dict):
                raise ResearchControlError("proposal must be a JSON object")
            payload = frontier.add_candidate(
                args.frontier_id,
                args.candidate_id,
                proposal,
                estimated_cost=args.estimated_cost,
            )
        elif args.action == "frontier-record":
            payload = frontier.record_result(
                args.frontier_id,
                args.candidate_id,
                outcome=args.outcome,
                actual_cost=args.actual_cost,
                score=args.score,
            )
        elif args.action == "frontier-rank":
            payload = frontier.rank(args.frontier_id)
        elif args.action == "bench":
            cases_path = (
                args.cases.resolve()
                if args.cases.is_absolute()
                else (args.root / args.cases).resolve()
            )
            responses_path = (
                args.responses.resolve()
                if args.responses.is_absolute()
                else (args.root / args.responses).resolve()
            )
            root = args.root.resolve()
            try:
                cases_path.relative_to(root)
                responses_path.relative_to(root)
            except ValueError as exc:
                raise ResearchControlError("ResearchBench inputs must stay in the repository") from exc
            responses = json.loads(responses_path.read_text(encoding="utf-8"))
            if not isinstance(responses, dict):
                raise ResearchControlError("ResearchBench responses must be a JSON object")
            payload = run_research_bench(cases_path, responses)
        else:  # pragma: no cover - argparse owns command validation
            parser.error(f"unsupported command: {args.action}")
    except (json.JSONDecodeError, OSError, ResearchControlError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
