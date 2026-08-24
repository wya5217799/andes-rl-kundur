# ANDES/Kundur research-skill adapter

Apply this file whenever an internal workflow module or external literature,
research-planning, writing, figure, review, or submission skill operates here.
This is the only ANDES-specific adapter; modules remain subordinate to
`kundur-round` and external skills remain project-neutral.

## Bootstrap and scope

1. Run `python memory/tools/session_context.py --json`.
2. Read only its bounded `required_reading`.
3. For manuscript work, record the selected `manuscript_line`, `read_scope`,
   `write_scope`, and venue state before acting.
4. Write only inside the selected line's declared `write_scope`. Source
   conference papers, other manuscript lines, `results/`, and the research
   ledger are read-only unless a separate repository workflow authorizes a
   change.
5. If a round is active, close it before manuscript work. If the programme has
   an authorized research goal, its prospective contract outranks a skill
   recommendation.
6. A global workflow-load recommendation does not authorize project writes.
   Map it through `skills/kundur-round/SKILL.md` section 2; user authorization
   plus the project-native `scratch`, `manuscript`, or `evidence` lane owns the
   actual writable surfaces and verification load.

## Ownership and handoffs

| Role | Owns | Must return | Never owns |
|---|---|---|---|
| **Project state owner** | `kundur-round` lane choice, round/claim/feed lifecycle, seals, formal execution authority, manuscript-line write scope | Canonical project artifact and repository checks | A global skill's private state machine |
| **Academic route owner** | Research depth, academic gate order, scientific acceptance criterion | One bounded route card or academic artifact | Project writes, experiment launch, engineering route selection |
| **Engineering route owner** | When explicitly invoked, Ask Matt selects the smallest engineering route; the selected engineering skill owns implementation and tests | Verified code/test/automation artifact back to the academic gate | Research question, evidence status, claim, verdict, or manuscript state |
| **Audit owner** | Its named evidence, domain, prose, or submission check over an existing input | PASS/QUALIFIED/FAIL plus bounded correction | Repairing the input silently or creating a parallel ledger |

At every transition, record current owner, required input, authority/write
scope, return artifact, return verification, next owner, and stop condition.
Only one owner is active for a deliverable. A missing required input stops the
handoff; it does not authorize the receiver to invent project state. Passing
engineering checks returns an implementation artifact only and never upgrades
scientific evidence.

## Evidence authority

Apply this precedence:

1. final formal guards and validity artifacts;
2. current `memory/claims/CLM-*.md`;
3. the selected line's feed reports;
4. sealed summaries, traces, hashes, and provenance under `results/`;
5. final round `verdict.md`;
6. manuscript skeletons, prose, literature views, and skill output.

Bind each headline result to a current claim and a stable artifact locator, not
only a round number. Follow supersession. A completed trace count cannot
override `INVALID`. Preserve negative, partial, excluded, unmeasured, and
superseded evidence.

## Mandatory power-system checks

- Separate frozen 50-Hz controller semantics from reported 60-Hz physical
  endpoints.
- Separate common-frequency restoration, relative synchronization, and
  inter-area endpoints.
- Report physical endpoints alongside legacy composite or reward metrics.
- Check actuator authority, energy, saturation, amplitude, slew, timing, units,
  signs, and information pattern.
- Treat recurrent-target-defect checkpoints as legacy evidence unless the
  specific result is independently corrected.
- Distinguish centralized, shared-policy, and decentralized causal objects.
- Require unseen graphs for topology-generalization language and separate
  evidence for safety, cross-simulator, HIL, or deployment claims.
- Preserve corridor/reactance scaling as a declared proxy unless a unit-valid
  SCR conversion exists.

## Manuscript-line boundary

When a line says its experiment side is complete, classify new reviewer
requests as:

1. fatal contradiction in existing evidence;
2. manuscript repair using existing evidence;
3. future work outside the current line.

Only the first category can block scientific validity. A skill suggestion does
not authorize a new round, reopen sealed analysis, or edit a different paper.

## Generated-document routing

- One-line-specific Deep Research output: register under that line.
- Cross-line reusable investigation: place under `docs/research/` and register
  it as a shared read dependency.
- Reviewer working notes and independent passes: keep under `tmp/<line>/`.
- Durable review: persist one consolidated, action-bearing report only when the
  line manifest registers its purpose, inputs, status, and supersession.
- Never copy measurement tables, claim cards, or verdict prose into a research
  or review document.

## Feed-first publication handoff

Use this exact order after final machine-readable decisions exist:

1. Reserve the claim ID as an identity-only stub; it is not yet a registered
   scientific claim.
2. Draft the canonical feed first with bounded Observations, Conclusions, and
   Limits tied to the final decision artifacts.
3. Audit that same feed with the evidence auditor and then the domain auditor.
   Do not audit a temporary substitute, detached claim sheet, manuscript draft,
   or reviewer-created copy. Detailed auditor notes stay in the conversation or
   `tmp/`.
4. Write only the audit decision summary into that feed's Publication gate.
5. Finalize the claim card to the allowed wording and bind it back to the feed.
6. Run `feed_check.py`; only then may the verdict skeleton, manuscript mapping,
   or later writing owner consume the result.

The feed is the only durable audit input and return artifact for this
transition. A failed audit returns the same feed for bounded correction or
forces `STAY-OUT`; it does not spawn a second report.

## Paper-writing control mapping

Apply the global navigator's `paper-writing-protocol.md`, with these
project-native mappings:

- Any external `Evidence Map` is a temporary view over current CLM cards,
  experiment feeds, formal verdicts, and stable result locators. It must not be
  persisted as a second evidence ledger.
- The ARS `Material Passport` maps to the selected `LINE.md`,
  `ARTIFACTS.json`, required reading, and current gate results. It may be used
  as an in-session handoff, but it never becomes a parallel project state.
- An ARS Claim Registry maps every manuscript claim back to current CLM IDs and
  feed/result locators. ARS advisory classifications cannot overwrite claim
  status.
- Paragraph evidence bindings and reviewer precommitments default to
  `tmp/<line>/`. If a future session genuinely needs them, consolidate them
  into one registered manuscript argument contract. Do not create one
  permanent planning file per section, reviewer, or pass.
- ARS block markers, manifests, patches, and apply reports are working revision
  artifacts under `tmp/<line>/` unless a response or re-review round requires a
  registered consolidated record. Markers never enter the submission source.

For full-paper generation, use `paper-writer` for evidence-bearing body prose,
`intro-drafter` after body commitments stabilize, and `paper-polish` only after
scientific and structural changes settle. Use ARS plan or outline only when the
argument chain is broken; use ARS patch/re-review controls for material
revision. Do not run the ARS full pipeline by default in this repository.

The review order is fixed by consequence:

1. canonical feed exists and its claim-to-artifact evidence audit runs;
2. the power-system domain audit runs on that same feed;
3. bounded external-context research only when the gate requests it;
4. focused broad manuscript review;
5. ARS multi-role review only when independence or controlled re-review changes
   the decision.

A failed item in steps 1-3 blocks polish and submission-readiness language.

## Venue boundary

The active `LINE.md` and its dated journal decision record own venue state.
Official journal scope, article types, fees, and policies must be refreshed
from official sources. Institutional ranking requirements must be confirmed by
the author or institution. A venue recommendation cannot strengthen scientific
claims or authorize new evidence.
