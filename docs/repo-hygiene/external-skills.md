# Skill ownership and external adapters

External skills are optional perspectives, not project authorities. The
canonical round lifecycle, claims, questions, gates, and manuscript feed
contracts remain owned by `skills/kundur-round/SKILL.md` and the schemas under
`memory/`.

## Project-maintained workflow

`kundur-round` is the only project skill entrypoint. Five workflows authored
and repeatedly repaired from repository friction remain local as internal
references: research junction, execution readiness, evidence audit,
power-system audit, and submission audit. Their exact triggers live only in
`skills/kundur-round/references/module-routing.md`; they have no `SKILL.md`
frontmatter or `agents/openai.yaml`, so discovery cannot select them.

Change the entrypoint or its modules only through a repository maintenance task
backed by a concrete failure or repeated friction pattern, then run the module
contract tests, scope checker, and repository health. The external-skill
adapter remains `skills/kundur-round/references/research-skill-adapter.md`.

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

The drafting/revision order lives in
`skills/kundur-round/references/paper-writing-protocol.md`; repository-specific
mappings live only in the project adapter.

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
`docs/repo-hygiene/research-skills.scope.json`: that manifest governs this
project's research workflow portfolio. The Tutor is read-only; the
enrichment writer has one narrow, user-authorized teaching destination and no
research authority.

## Engineering routers

Two peer engineering routers are reachable from the session skill catalog and
serve scoped code work. Neither sits in the academic scope manifest and neither
may mutate rounds, claims, questions, gates, feeds, or manuscript-line state;
they return implementation artifacts only.

- **`ask-matt`** — the engineering flow: idea → spec → tickets → `/implement`
  (which drives `/tdd` + `/code-review`); use only when the user names it.
- **`diagnosing-bugs`** — the bug-finding discipline: build a tight red loop
  before theorising, fix with a regression test, then post-mortem; hands off to
  `/improve-codebase-architecture` when no correct seam exists.

Selection is a peer engineering decision; the research-junction module does not
discover or nested-route through them. `skills/kundur-round/SKILL.md` section 2
and the current user authorization still decide the writable lane.

## Invocation and scope manifest

`docs/repo-hygiene/research-skills.scope.json` is the single inventory of the
project entrypoint, internal modules, and external academic skills. It records
exact project paths, external invocation policy, and empty external
project-write authority.
Source roots, one-primary selection, precedence, and collision handling live
only in `docs/repo-hygiene/skill-routing.md`.
Engineering workflow routers are intentionally outside this academic scope.
If the user explicitly invokes one, it operates as a separate peer request
under its own authority contract; the research-junction module does not discover or
nested-route through it.

The research-junction module may issue a workflow-load recommendation (`scratch`,
`manuscript`, or `evidence`) to keep routing proportional. That recommendation
does not expand project write authority: `skills/kundur-round/SKILL.md`
section 2 and the current user authorization make the binding lane and scope
decision. Ask Matt remains a peer engineering router and cannot mutate the
research ledger or manuscript-line state. It must not be added to the academic
scope manifest or the external capability inventory. The project adapter's
`Ownership and handoffs` table is the single repository-specific owner map;
this page only records the installation boundary.

Validate installation, duplicate names, invocation policy, and accidental
project-specific text in global packages with:

```powershell
python memory\tools\check_skill_scope.py `
  --strict --scope-manifest docs\repo-hygiene\research-skills.scope.json
```

High-cost external judgment workflows are explicit. Narrow external
presentation helpers may be selected on an exact match. Project audit and
efficiency gates are reached only through the checked-in project workflow.

## Agent-facing writing standard

`writing-for-agents` is the default writing reference for every repository
document whose reader is an agent: `AGENTS.md`, `CLAUDE.md`, `skills/`,
`docs/agents/`, `docs/repo-hygiene/`, and ledger templates. Load it before
creating or editing such a document. It owns writing mechanics only — context
pointers, the information hierarchy, steps with completion criteria, leading
words, pruning, single source of truth. It has no authority over rounds,
claims, gates, ledgers, or manuscript-line state, and project-specific
research rules are never copied into it. Schema-enforced contracts (feed,
claim, plan, and verdict forms) keep their `validate.py` shapes; the skill
governs the prose around them, not the contracts.
