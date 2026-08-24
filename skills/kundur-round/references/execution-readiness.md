# Execution Readiness Module

Internal reference of `kundur-round`; it is not a discoverable or independently
invocable skill.

Run a stage gate before launch or reconfiguration. Optimize time to a valid decision and completed valid jobs per hour, not CPU percentage.

## Authority boundary

Read [the repository workflow](../SKILL.md) and bind the card to
the owning scientific plan, active-run state, and user authorization. Let those
sources define the question, design, thresholds, evidence, claims, and
permission to act. This module checks execution readiness only.

Source every numeric guard, reserve, margin, retry count, and throughput threshold from project policy, user instruction, host baseline, or measurement. Apart from the observation-cadence defaults stated below, keep an unknown quantity symbolic and name the measurement needed to resolve it; an invented precise number is not a conservative plan.

## 1. Bind the execution contract

Recover:

- decision and authoritative plan;
- stage: `probe`, `rehearsal`, `pilot`, or `formal`;
- jobs, dependencies, and formal completion requirement;
- known runtime, memory, threads, accelerator use, and output per job;
- authorized wall-clock, compute or spend, and artifact budgets;
- simulator, licence, operating-system, project, and shared-host caps;
- whether each concurrency limit is a hard cap or a derived execution budget;
- prospective stop, retry, interruption, and terminal-artifact rules.

Classify the run:

- **Quick:** known path and expected end-to-end time at most about five minutes.
- **Tunable:** probe, rehearsal, or pilot whose execution settings may still change.
- **Frozen:** formal, sealed, protected, or holdout execution.

For a frozen run, read [formal-execution.md](formal-execution.md) before planning or monitoring it.

Treat placeholders, guesses, stale measurements, inherited defaults, and unresolved unknowns as unresolved inputs. A named policy is a hard cap only when it is an intentional ceiling independent of throughput; an inherited or previously convenient worker count is a derived budget. Name the owner or measurement that can resolve each unknown; do not let test-fit content silently become a launch premise.

**Complete when:** every execution decision and numeric value can be traced to an authority or measurement, or is explicitly symbolic and assigned a measurement before formal launch; every concurrency limit is classified as a hard cap or derived budget.

## 2. Choose the cheapest decisive stage

Advance only as far as the current decision requires:

1. **Probe** — reject broken assumptions, models, inputs, or invariants.
2. **Rehearsal** — measure runtime and resource shape; validate launcher, artifacts, and failure handling.
3. **Pilot** — run the smallest scientifically meaningful comparison allowed by the design.
4. **Formal** — execute the complete frozen evidence contract.

Use fast-negative checks before expensive positive evidence. Label each stage honestly. For a quick, familiar task, use the trusted runner directly when authorized; avoid benchmarking that costs more than it can save.

**Complete when:** the selected stage is the least expensive one that can answer exactly the decision claimed for it, with its escalation gate stated.

## 3. Freeze prospective stops

Separate:

- **Engineering invalidity:** crash, invariant violation, corrupt artifact, exhausted disk reserve, out-of-memory risk, or another condition that makes the run unusable.
- **Scientific early stop:** a prospectively defined rule whose inference remains valid. A counterexample may stop a universal claim only when the scientific contract explicitly permits that logic.
- **Completion:** the planned evidence bank or other formal completion condition.

Preserve failed attempts and distinguish rehearsals from formal attempts. Attach every retry to an existing prospective rule or return it to the owner for authorization.

**Complete when:** each terminal state has an observable trigger, required artifacts, and next owner, all fixed before scientific outcome visibility.

## 4. Set the resource budget and concurrency

Set worker concurrency no higher than the minimum of:

- independent ready jobs;
- measured CPU and native-thread capacity;
- memory capacity after an explicit system and shared-workload reserve;
- accelerator, licence, simulator, project, and user caps;
- sustainable disk and logging throughput.

Subtract resources reserved by other running work. Account for native threads inside each worker to prevent nested oversubscription. Preflight peak memory, free disk, output growth, logging, and parent-process buffering.

### Plumbing check versus capacity evidence

A **plumbing check** proves that workers start, overlap, isolate their writable
paths, preserve provenance, and exit as intended. **Capacity evidence** uses a
representative workload to justify the proposed worker/thread budget against a
hard cap or a measured limiting bottleneck. A plumbing check is not capacity
evidence.

For a tunable precursor to a non-quick or formal run with unknown resource
shape, use a **capacity ladder**: measure representative work, raise workers in
small steps, and compare aggregate completed-job throughput, peak memory, I/O
wait, startup cost, failures, and tail latency. Freeze the highest safe level
before formal launch. Stop increasing when added workers cross the sourced
marginal-throughput threshold or approach a guard.

Keep every capacity rung, including rejected and failed rungs, in the owning workflow's existing operational artifact. Record at least the configuration identity, concurrency and thread limits, elapsed time, valid completions, peak resource telemetry, terminal status, and reason. Do not create a second global ledger.

When independent jobs and unused resource headroom remain, require either an
intentional hard cap or a measured bottleneck that explains the chosen budget.
If neither exists before the seal, return **MEASURE-FIRST**. Calling an
unmeasured inherited budget conservative does not resolve it.

For short jobs, compare wall-time savings with launcher, debugging, coordination, and merge overhead. Prefer serial or modest concurrency when parallel engineering costs more than it saves. Treat low CPU as a diagnostic clue; identify the bottleneck and ready work before adding processes. Generate neither duplicate experiments nor synthetic load merely to raise utilization.

**Complete when:** plumbing and capacity are recorded separately; every cap is classified; capacity evidence is either hard-cap-bounded or representative-measured; all shared-host reservations are subtracted; and the expected execution fits the authorized time, compute or spend, and artifact budgets.

## 5. Estimate duration and observation cadence

For `J` independent jobs, concurrency `c`, per-job runtime range `[t_low, t_high]`, setup time `s`, and serial finalization time `a`, start with:

```text
waves = ceil(J / c)
ETA = s + waves * [t_low, t_high] + a
```

Add measured queue, launch, I/O, straggler, and teardown overhead. Report an ETA range, its evidence, confidence, and next recalibration point. Recalibrate from a rehearsal or first completed wave when the execution contract permits it.

Prefer event-driven completion and failure notification. Otherwise:

- for at most about five minutes remaining, wait once or check near completion;
- for longer work, start near 10% of remaining ETA and clamp to roughly 2–60 minutes;
- lengthen the interval when no action is possible between checks;
- shorten it only near an actionable resource or deadline guard;
- wake immediately on completion, failure, or required attention.

Until an ETA exists, leave the polling interval unset. Use the defaults above as written unless an authoritative deadline, resource guard, or measured action window supports a different number.

When persistent workers and durable status artifacts make the run safe unattended, yield or close the active conversation and use one low-frequency heartbeat. Make it report only actionable operational state, avoid repeating unchanged detail, and stop at the terminal condition.

**Complete when:** the ETA accounts for waves and overhead, and every scheduled observation can trigger a defined action or terminal handoff.

## 6. Emit the card, then act or hand off

Lead with exactly one execution-readiness status:

- **RUN-READY:** the card is complete; for a proposed non-quick or formal run,
  capacity evidence is sufficient; execution may proceed only under authority
  already granted elsewhere.
- **MEASURE-FIRST:** one named, authorized, non-claim-bearing probe or
  rehearsal can resolve the remaining execution or capacity unknown before the
  seal.
- **HOLD:** authority, scientific contract, or a safe and valid measurement
  path is missing, or the requested resize conflicts with an active frozen
  attempt; do not launch, resize, or retry.

These statuses judge execution readiness only. They do not decide whether a research idea is worthwhile, whether a study design is valid, or whether evidence supports a claim.

Use this schema:

```markdown
Experiment efficiency card
- Execution readiness: RUN-READY | MEASURE-FIRST | HOLD
- Decision and authority:
- Stage and scientific contract source:
- Run state: pre-seal tunable | frozen not started | active | terminal
- Cheapest decisive work and escalation gate:
- Completion, stop, retry, and interruption rules:
- Jobs and dependencies:
- Resource evidence, reservations, and time/compute/spend/artifact budget:
- Unresolved inputs and resolution owner or measurement:
- Plumbing check:
- Capacity evidence and cap classification:
- Concurrency and limiting bottleneck:
- Expected resource use and unused-capacity explanation:
- ETA range, basis, and recalibration point:
- Progress signals and observation cadence:
- Authorized action or next owner:
```

For a quick run, compress the card to readiness status, decision, stage, concurrency, ETA, and terminal check. For a frozen or multi-hour run, fill every field.

Execute through the project-native runner when already authorized; otherwise return the card to the current owner. Preserve durable terminal evidence and report the exact terminal state.

Before returning the card, audit every numeric literal. Retain it only when it comes from an authority, a measurement, the user's inputs, or an explicit default in this skill; otherwise replace it with a named symbolic quantity and the measurement that will resolve it. Then verify that the readiness status matches the unresolved-input field.

**Complete when:** the card contains every field required for its branch, every number passes the numeric audit, plumbing and capacity evidence are not conflated, the readiness status agrees with the capacity-evidence field, and the execution action stays within the recovered authority.
