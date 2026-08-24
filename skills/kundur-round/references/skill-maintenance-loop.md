# Skill Maintenance Loop

Use this reference only in a user-authorized maintenance task over the project
workflow or its external-skill adapters. It turns observed execution failures
into bounded local changes; it is not an instruction to rewrite workflow files
during ordinary research work.

## 1. Require behavior evidence

Accept one severe failure or a repeated pattern from separate runs, such as:

- the user corrected the route or stage;
- the selected skill rejected the input the router promised;
- two skills produced the same deliverable;
- a hard gate appeared after expensive work had already begun;
- a completion criterion allowed an incomplete return;
- a branch was routinely loaded but rarely used;
- the user could not tell when the router should be invoked.

Record the exact prompt, selected route, observed result, expected behavior,
and consequence. General dissatisfaction without a reproducible behavior is a
diagnostic question, not yet a patch.

## 2. Establish ownership before editing

Classify every affected source:

- **Pinned or external:** preserve its files. Repair the local adapter, route,
  invocation policy, or upstream pin/update process.
- **Project entrypoint or module:** edit only the smallest source of truth that
  owns the failed behavior; modules never become new skill entrypoints.
- **Project authority:** follow repository governance and writable scope;
  neither an internal module nor external skill grants authority.

Record hashes for external skills when the maintenance task touches adjacent
local routing, then verify those hashes again at closeout.

## 3. Diagnose with the skill-writing vocabulary

Classify the failure as one or more of:

- invocation or description mismatch;
- branch or progressive-disclosure failure;
- weak or missing completion criterion;
- duplication or competing sources of truth;
- sediment, sprawl, or no-op instructions;
- missing handoff or authority boundary.

Prefer a sharper trigger, pointer, or completion criterion over a new skill.
Split only when the new branch has an independent invocation or when later
steps demonstrably cause premature completion.

## 4. Make the change falsifiable

Before editing, state the behavior that must change and the behavior that must
remain fixed. Add or update a forward test that fails on the observed defect
when the skill has an executable contract. Then apply the smallest patch.

Validate:

1. sole-entrypoint frontmatter and non-discoverable internal modules;
2. focused forward tests;
3. dependency and invocation policy;
4. project-scope leakage checks when an adapter exists;
5. external-skill hashes;
6. one worked routing example for the repaired branch.

## 5. Return a maintenance decision

Report:

```text
Observed failure:
Affected locally maintained source:
Change made:
Forward verification:
External skills preserved:
Residual uncertainty:
Next review trigger:
```

Use `NO CHANGE` when the evidence does not identify a local behavioral defect.
Do not optimize on a fixed run count: review on a severe failure, a repeated
pattern, a dependency or model change, or a deliberate periodic audit.
