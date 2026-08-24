# Handoff Contract

Use this contract whenever the route changes owners. It makes a skill chain a
sequence of checked artifacts rather than a group of simultaneously active
advisers. A repository adapter may supply project-specific artifact names and
write scopes; this global contract does not create or mutate project state.

## Card

```text
Current owner:
Required input:
Acceptance check:
Authority and write scope:
Return artifact:
Return verification:
Next owner:
Stop condition:
```

## Rules

1. Name exactly one current owner. Later owners remain inactive until the
   current owner returns its artifact and the return verification passes.
2. Required input names an existing artifact, decision, or bounded work order,
   not a hoped-for output. A missing required input is a stop, not permission
   to let the receiving skill invent it.
3. The current owner owns only its declared deliverable. It does not inherit
   the repository's experiment, evidence, claim, manuscript, or submission
   authority unless repository governance grants that scope independently.
4. The return artifact is the smallest durable or ephemeral object the next
   owner actually needs. Do not create parallel ledgers, duplicate review
   reports, or intermediate documents with no downstream reader.
5. A router chooses ownership and stopping gates; a specialist produces or
   verifies the artifact; repository governance owns project state. An
   explicitly invoked peer router chooses its own domain route and is never a
   nested child of this navigator.
6. Passing an engineering return verification proves the implementation
   contract only. Passing an academic review proves only that review's stated
   gate. Neither result silently authorizes an experiment or strengthens a
   scientific claim.

## Completion

A handoff is complete only when the required input existed before work began,
the current owner stayed inside its authority and write scope, the named return
artifact exists, its verification passed, and exactly one next owner (or
`none`) is recorded.
