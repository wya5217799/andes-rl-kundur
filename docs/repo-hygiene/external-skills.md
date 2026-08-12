# External skill adapters

External skills are optional perspectives, not project authorities. The
canonical round lifecycle, claims, questions, gates, and manuscript feed
contracts remain owned by `skills/kundur-round/SKILL.md` and the schemas under
`memory/`.

## Academic research suite

`academic-research-suite` may be invoked explicitly for literature, writing,
experiment-planning, or review assistance. It must not:

- reserve or mutate project rounds, claims, or questions;
- change research-program gates or sealed verdicts;
- create a second project ledger or replace `memory/STATE.md`; or
- write project files unless the current user request independently authorizes
  that edit and the edit follows repository governance.

For manuscript work, ARS supplies argument-recovery, integrity, patch-revision,
rebuttal, and multi-role re-review controls. Its full academic pipeline is not
the default inside this governed repository. Any Material Passport, Claim
Registry, or pipeline progress state is an in-session adapter over the active
manuscript line and existing ledgers, not a durable parallel authority.

The suite is installed globally at
`$CODEX_HOME/skills/academic-research-suite`, outside this repository. Its
pinned sources, commits, license, adapter version, manifest hash, and update
method are recorded in `docs/repo-hygiene/external-skills.lock.json`.

The exact snapshot removed from the repository is recoverable from Git commit
`54ab40b` and from the verified global installation. Updating it requires
rebuilding from the pinned upstream sources, verifying the manifest hash, and
changing the lock in the same review.

## Supervisor Skills

The eleven skills adapted from `HKUSTDial/Supervisor-Skills` are also installed
globally. They contribute focused literature, idea, paper-structure, drafting,
figure, polishing, and review workflows. Their pinned source commit and license
are recorded in `docs/repo-hygiene/supervisor-skills.lock.json`.

These skills do not own ANDES state. When they operate here, the project
adapter at `skills/kundur-round/references/research-skill-adapter.md` supplies
the evidence hierarchy, physical checks, manuscript boundary, and generated-
document routing.

For paper production, use `tech-paper-template` to establish the logic chain,
`paper-writer` for evidence-bearing body prose, `intro-drafter` after the body
commitments stabilize, and `paper-polish` only after material changes settle.
Their Evidence Map is a working view over the existing feed, claims, and result
locators. It is not registered as another evidence ledger.

The global division and drafting/revision order live in
`ask-research-supervisor/references/paper-writing-protocol.md`; the repository-
specific mappings live only in the project adapter.

For investigation depth, use `research` for one bounded primary-source
question or evidence gap and `deep-research` for a multi-perspective literature
landscape, nearest-work map, or method-family synthesis. Do not run both on the
same deliverable by default.

## Atomic STEM Tutor

`atomic-stem-tutor` is explicit-only. Select it only when the user invokes
`$atomic-stem-tutor`; ordinary requests to understand the repository, a
subsystem, or a scientific concept receive a direct answer. Its Repository mode
is read-only. Only an explicit `$enrich-project-learning` request may maintain
the non-authoritative learning assets under `learning/`.

The enrichment writer records transferable foundation atoms and their
`requires` and `used-in` relations. Neither skill may treat project-local
identifiers, experiment verdicts, paper claims, or implementation symbols as
foundation atoms; mutate research rounds or evidence ledgers; or use
`learning/` as evidence. Ordinary learning and coding requests trigger neither
skill. Chat-derived atoms remain outside the project graph unless the user
explicitly requests an import and the candidate is revalidated against live
repository anchors.

These teaching skills are intentionally outside
`docs/repo-hygiene/research-skills.scope.json`: that manifest governs academic
research skills with no project-write authority. The Tutor is read-only; the
enrichment writer has one narrow, user-authorized teaching destination and no
research authority.

## Invocation and scope manifest

`docs/repo-hygiene/research-skills.scope.json` is the single inventory of
global academic skills used by this repository. It records which skills may
be invoked implicitly and asserts empty project-write authority.
Engineering workflow routers are intentionally outside this academic scope.
If the user explicitly invokes one, it operates as a separate peer request
under its own authority contract; the research supervisor does not discover or
nested-route through it.

The Supervisor may issue a workflow-load recommendation (`scratch`,
`manuscript`, or `evidence`) to keep routing proportional. That recommendation
does not expand project write authority: `skills/kundur-round/SKILL.md`
section 2 and the current user authorization make the binding lane and scope
decision. Ask Matt remains a peer engineering router and cannot mutate the
research ledger or manuscript-line state. It must not be added to the academic
scope manifest or the Supervisor dependency inventory. The project adapter's
`Ownership and handoffs` table is the single repository-specific owner map;
this page only records the installation boundary.

Validate installation, duplicate names, invocation policy, and accidental
project-specific text in global packages with:

```powershell
python C:\Users\27443\.codex\skills\ask-research-supervisor\scripts\check_dependencies.py `
  --strict --scope-manifest docs\repo-hygiene\research-skills.scope.json
```

High-cost judgment workflows such as Deep Research, Idea Evaluator, full
drafting, and complete pre-submission review are explicit. Narrow presentation
helpers and hard evidence/domain/submission gates may be selected implicitly
when the task clearly matches.
