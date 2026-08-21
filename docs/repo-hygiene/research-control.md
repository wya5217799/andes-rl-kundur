# Research control plane

Use `python memory/tools/research_control.py` when an agent needs one
machine-readable operational view across rounds, long jobs, artifact provenance,
safe reproduction planning, bounded scratch candidates, or ResearchBench.

The interface is non-authoritative. It never reserves a round, launches a
scientific command, registers a claim, edits a feed, creates a formal seal, or
writes paper-facing output. Round plans, seals, results, feeds, claims, and
project gates remain the scientific authority.

Round phases are inferred from positive evidence only: rehearsal, formal seal,
material output, round-bound feed reports, round-citing claims, and verdicts.
Insufficient evidence yields `unknown` or `inconsistent`, never a guess.

## Command families

| Need | Command family | Writes |
| --- | --- | --- |
| Current project mode and lifecycle | `state` | none |
| Recoverable long-job history | `job-*` | `tmp/research-control/jobs/` only |
| Hash, seal, claim, and feed provenance | `trace` | none |
| Prerequisite-checked reproduction advice | `reproduce` | none; never executes |
| Finite advisory candidate search | `frontier-*` | `tmp/research-control/frontiers/` only |
| Frozen governance incident replay | `bench` | isolated temporary workspaces only |

All successful outputs carry an `andes-research-control/*.v1` schema. Runtime
validation failures exit 4 with `andes-research-control/error.v1` JSON on
stderr. A reproduction response with `status=blocked` is a successful advisory
result; `execute` remains false and a blocked command is represented only by its
SHA-256 digest.

Operational metadata and events are hash-bound. Events use create-only,
per-sequence atomic files guarded by crash-releasing operating-system locks.
A terminal job event also writes a create-only hash-bound terminal record
binding the terminal event digest; readers fall back to the event chain when
that record is absent. Artifact traces include the declared command and its
digest when exactly one owner round declares it.
Scratch frontiers freeze candidate and compute budgets, retain terminal
failures, and rank successful candidates deterministically.

ResearchBench cases live in `tests/research_bench/cases/`. Each case materializes
its own synthetic workspace, invokes the same public control action used by the
CLI, checks protected-root immutability, and then scores the supplied research
decision. Benchmark output is evaluation-only and never scientific evidence.
