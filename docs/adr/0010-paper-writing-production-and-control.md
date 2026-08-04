# ADR-0010: Separate paper production from scientific control

- **Status:** Accepted
- **Date:** 2026-07-30
- **Deciders:** repository owner and Codex workflow review
- **Supersedes:** none
- **Related:** ADR-0008, ADR-0009,
  `skills/kundur-round/references/research-skill-adapter.md`

## Context

The repository can use both Academic Research Suite (ARS) and Supervisor
Skills. Each family covers paper writing, but they optimize different things.
Supervisor Skills provide direct technical-paper logic and evidence-bounded
prose generation. ARS provides a larger state machine, independent reviewer
roles, claim and citation integrity controls, patch-based revision, and
re-review traceability.

Selecting either family as the sole paper writer creates a failure mode.
Supervisor-only writing lacks durable control for material revisions and
multi-role re-review. ARS-only writing duplicates the repository's manuscript
line, claim ledger, artifact manifest, and publication gates, while adding
checkpoints and process artifacts that are not useful for every section.
Running both end to end creates competing Evidence Maps, Claim Registries,
Material Passports, reviewer reports, and progress states.

The previous navigator routed story, draft, review, and revision as adjacent
skill names but did not define who owned paragraph evidence bindings,
cross-section commitments, material revision, or the final scientific gate.
That ambiguity could produce polished prose whose claim strength had drifted
from the sealed experiment feeds.

## Decision

Adopt a production-and-control split.

1. **Project evidence owns truth.** CLM cards, feeds, formal verdicts, and
   result locators define allowed claims and tested scope.
2. **Supervisor Skills produce the manuscript.**
   `tech-paper-template` establishes the technical argument chain;
   `paper-writer` drafts evidence-bearing body sections; `intro-drafter`
   drafts the Introduction after body commitments stabilize; `paper-polish`
   performs faithful language-only repair.
3. **ARS supplies control mechanisms selectively.** Use ARS plan or outline
   when the argument chain is unresolved, patch or rebuttal modes for bounded
   material revision, and the reviewer workflow for independent multi-role
   review or controlled re-review. Do not run the full ARS academic pipeline
   by default.
4. **Specialist auditors are hard gates.** Claim-to-artifact and power-system
   reviews precede broad presentation review. Journal-package review runs on
   the final compiled package.
5. **External working records are adapters.** Supervisor Evidence Maps and ARS
   Material Passports or Claim Registries map to existing project records.
   They remain ephemeral unless consolidated into one registered manuscript
   argument contract.
6. **Revision is classified before editing.** Language-only changes use
   polishing; bounded material changes use issue- or block-scoped control;
   structural rewrites reopen the argument stage and trigger whole-draft
   re-audit.

The global orchestration contract is
`ask-research-supervisor/references/paper-writing-protocol.md`. This
repository's mappings and review order are owned by
`skills/kundur-round/references/research-skill-adapter.md`.

## Rejected alternatives

### Use ARS full pipeline for every paper

Rejected because this repository already has authoritative research,
manuscript-line, evidence-feed, artifact, and venue state. A second persistent
pipeline would increase context, checkpoint cost, and drift risk.

### Use only Supervisor Skills

Rejected because direct generation and a broad pre-submission review do not
provide the same untouched-block protection, revision traceability, or
independent multi-role re-review as the relevant ARS mechanisms.

### Merge or rewrite the upstream skills

Rejected because it would duplicate maintained upstream knowledge, blur
licenses and update boundaries, and create a third writing system. The router
should compose stable interfaces rather than fork implementations.

### Run every reviewer on every draft

Rejected because overlapping reviews multiply reports without necessarily
changing the decision. Review depth is selected by the consequence and
uncertainty of the current gate.

## Consequences

- The default writing path is now explicit: evidence gate, argument contract,
  body prose, Introduction, cross-section audit, domain and broad review,
  controlled revision, polish, and submission audit.
- A new task can enter at one bounded section without paying for an entire ARS
  pipeline.
- Material revisions receive stronger drift protection than language-only
  edits.
- New sessions read the manuscript line and artifact manifest rather than
  multiple skill-native ledgers.
- The combination is intentionally asymmetric: Supervisor Skills write most
  prose; ARS is invoked only where its control mechanism adds a distinct
  guarantee.
