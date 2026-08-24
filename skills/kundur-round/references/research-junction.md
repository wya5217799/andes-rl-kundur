# Research Junction Module

Internal reference of `kundur-round`; it is not a discoverable or independently
invocable skill.

Act as a research-junction navigator. Recover live state, identify the current
blocking decision, assign one owner to a checkable return, and continue only as
far as the selected execution mode authorizes.

Complete the `kundur-round` bootstrap first, then apply
[the project research adapter](research-skill-adapter.md).
That adapter owns project authority, evidence precedence, and writable scope.

## Execution mode

- **Advice:** route one decision and return one concrete next action.
- **Gate:** execute one authorized gate and stop after one verified return.
- **Mission:** carry an explicitly authorized multi-gate mission to its
  terminal condition with quiet progress.

Default to Advice for an open-ended routing question. Use Gate for a bounded
action. Use Mission when the user requests a long-running, end-to-end,
finish-oriented, babysitting, monitoring, or “do not stop” outcome and its
authority boundary is clear. Mission mode changes continuity, not authority.

Modern AI can perform ordinary method, statistics, counterargument, and writing
checks inside the selected gate. Add a specialist only when it contributes a
different evidence source, tool, authority, or return artifact.

## 1. Recover the junction

Inspect available context first. Establish:

- the research object and run state: idea, prospective plan, tunable run,
  frozen active run, terminal result, claim, draft, or submission package;
- one decision question and its consequence: `advisory`,
  `prospective-change`, `frozen-change`, or `claim-bearing`;
- the governing authority, writable scope, current owner, existing input, and
  blocking gate.

**Complete when:** one object, one decision, one authority, one owner, and one
blocking gate are explicit.

**Continuity shortcut:** when a prior gate in this conversation already
established the junction and nothing relevant changed (same object, same
decision, same authority), reuse it instead of re-deriving; only re-check the
specific fields the new question touches.

## 2. Select one gate

Select the smallest gate that can answer the decision:

1. **Direction:** is the question worth pursuing?
2. **Design:** can the study identify the intended conclusion?
3. **Readiness:** is the authorized study ready to execute or monitor?
4. **Result:** are completed outputs valid and interpretable?
5. **Claim:** what is the strongest conclusion the evidence permits?

Use [research-experiment-protocol.md](research-experiment-protocol.md)
for the five gates. Read the branch needed now:

- [routing-map.md](routing-map.md) for the decision-to-owner map;
- [paper-writing-protocol.md](paper-writing-protocol.md) for an
  argument, figure, draft, review, or revision;
- [venue-gate.md](venue-gate.md) for venue decisions;
- [comparison-identifiability-gate.md](comparison-identifiability-gate.md)
  before freezing or claiming a comparison;
- [review-bundles.md](review-bundles.md) for a formal experiment
  red-team, terminal-result challenge, or comprehensive pre-submission review;
- [long-task-protocol.md](long-task-protocol.md) for Mission mode,
  long-running execution, monitoring, quiet progress, or multi-gate work;
- [handoff-contract.md](handoff-contract.md) when ownership changes;
- [workflow-recipes.md](workflow-recipes.md) only for a genuinely
  multi-gate request.

The five gate definitions above are the working core; reach for a reference
only when the decision needs its branch-specific detail.

This module owns route-card grammar only. It may describe Gate or Mission
continuity after `kundur-round` has selected and authorized that branch;
`kundur-round` remains the only process owner and owns experiment identifiers,
execution, evidence records, domain gates, write scopes, and authorization.

## 3. Assign one owner

Choose one primary owner. Add at most one supporting audit, and only when its
distinct artifact can change the gate decision.

A declared review bundle counts as one bounded owner. Its internal passes read
the same frozen input and return one consolidated decision rather than creating
competing routes.

Installed does not mean invoked. Mark the route as:

- `executable-now` when the user already invoked the owner or its policy allows
  selection;
- `explicit-handoff` when the user must invoke it explicitly.

A suite such as Academic Research Suite may own one bounded workflow and mode.
Fix its input, return, and stop condition; do not transfer project-routing
authority or start a full suite by default.

Read every selected skill's `SKILL.md` completely and preserve its completion
criterion and output contract.

## 4. Route, execute, and finish

Use this short card unless an ownership change requires the full handoff card:

```text
Decision gate:
Primary owner:
Required input:
Return artifact and acceptance check:
May change the active run:
Invocation:
Stop condition:
```

- Advice returns the route and one concrete next action. For Advice the card
  may shrink to its routing core -- gate, owner, next action, stop condition --
  and may return inline rather than as a persisted artifact.
- Gate stops after one verified return.
- Mission continues across accepted gates when each next action is already
  authorized by the mission contract. Read
  [long-task-protocol.md](long-task-protocol.md) and accumulate
  intermediate returns for one consolidated outcome.
- A passed gate validates its stated return; it does not by itself supply new
  authority for the next gate.
- Treat a frozen active run as monitor-only. Design, metric, comparator, or
  claim changes belong to an authorized amendment or successor attempt.
- Treat literature, idea evaluation, generic review, and external workflow
  outputs as advisory context, not project evidence.
- Treat engineering verification as proof of implementation, not scientific
  validity or experiment authority.
- Reuse project records instead of creating a second ledger.

Resolve conflicts in this order: user and project governance; active study or
manuscript records; canonical evidence and validity artifacts; current official
sources; router and reviewer outputs.

## Maintenance and finish

When an authorized maintenance task exposes a wrong gate, unusable handoff,
duplicate check, or late hard stop, read
[skill-maintenance-loop.md](skill-maintenance-loop.md) and repair the
smallest local source of truth.

Return the gate or mission outcome, unresolved blocker, and next eligible
route. Advice and Gate finish at the current gate; Mission finishes at its
verified terminal condition or a genuine authority boundary.
