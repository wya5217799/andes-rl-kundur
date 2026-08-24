# Long-Task Protocol

Use this protocol only in **Mission** mode: the user requested a long-running,
end-to-end, multi-gate, finish-oriented, or monitoring outcome and supplied or
accepted a sufficiently clear authority boundary.

Mission mode changes continuity, not authority. A terminal instruction such as
“finish,” “babysit,” or “do not stop” does not broaden authority, writable
scope, budget, evidence status, or permission for external actions.
A frozen active run remains monitor-only unless its governing authority already
provides an amendment or successor branch inside the mission contract.

## Mission contract

Settle this compact contract before sustained execution:

```text
Outcome:
Current authoritative state:
Permitted gates and actions:
Writable scope:
Budget or resource ceiling:
Terminal condition:
Pause-for-user conditions:
Resume evidence:
Progress policy: quiet
```

Infer fields from governing project records and the user's request when safe.
Ask only when a missing field would materially change the mission. A project
adapter may replace this card with its own authoritative state and lifecycle.

**Complete when:** the terminal condition is testable, the next action is
authorized, and every forced user checkpoint is explicit.

## Execution loop

1. Recover live state. On a resumed or long-running task, inspect existing
   processes and artifacts before any restart. Treat durable project state,
   not chat narration, as the resume authority.
2. Select the next blocking gate and one current owner.
3. Execute that owner to its checked return. Store gate detail in the declared
   project artifact or an ephemeral working note; keep chat as transport.
4. Advance automatically when the return passes and the next gate or action is
   already authorized by the mission contract. A gate pass supplies evidence,
   not new authority.
5. When a result fails or qualifies, follow the prospectively registered branch
   if it is in scope. Preserve failed and invalid artifacts.
6. Re-read authoritative state after a process completes, an owner changes, or
   a material artifact appears. Continue until the terminal condition or a
   pause-for-user condition is reached.

Do not turn every gate return into a user-facing deliverable. The mission owns
one final consolidated return unless the user requested staged deliverables.

## Quiet progress

Use commentary as a heartbeat, not a report.

- Send a compact start update after the mission contract is known.
- Send the next update only for a material milestone, changed state, genuine
  blocker, required authorization, or terminal return, plus any host-required
  heartbeat.
- Keep a heartbeat to one or two short sentences: current action and what
  changed since the last update. Omit repeated rationale, completed checklists,
  route cards, token counts, elapsed-time narration, and unchanged status.
- Accumulate intermediate gate results for the final return. Repeat the route
  card only when authority, owner, scope, or terminal condition changes.
- Treat unchanged external state as silent except for the host-required
  heartbeat. Use the available monitor or wait mechanism instead of frequent
  polling, and avoid narrating identical snapshots.

The host may display automatic elapsed or processed-time indicators. They are
runtime telemetry, not mission deliverables; do not restate them in commentary.

## Wait and resume

- Prefer a recurring monitor, bounded wait, or background process appropriate
  to the host. Avoid a blocking wait that prevents required communication.
- Before retrying, distinguish a running process, completed process, retained
  failure, missing artifact, and disconnected client.
- Resume from the last authoritative checkpoint. Reconstruct only missing
  ephemeral context; preserve formal inputs, outputs, seals, thresholds, and
  failure artifacts.
- A long wait is not a blocker by itself. Pause for the user only when the
  contract names the checkpoint or continuation needs new authority, external
  coordination, or a materially expanded budget or scope.

## Completion

Finish Mission mode when one of these is true:

1. the terminal condition is verified and the consolidated outcome is ready;
2. a named user checkpoint requires a decision;
3. progress requires authority or scope outside the mission contract;
4. an authoritative failure state forbids the next action.

Return the outcome, evidence and verification, unresolved uncertainty, and the
next eligible action. Include intermediate history only when it explains the
final decision or a retained failure.
