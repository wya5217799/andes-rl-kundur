# Skill routing and scope

This file is the repository's single skill-selection contract. A skill supplies
a method; it never acquires project authority from where it is installed.

## Source scopes

| Scope | Typical location | Meaning here |
|---|---|---|
| repository-private | `skills/<name>/SKILL.md` | Self-maintained entrypoint versioned and tested with repository feedback; this repository has one: `kundur-round`. |
| internal module | `skills/kundur-round/references/` | Branch detail loaded only by `kundur-round`; not discoverable or independently invocable. |
| shared-global | `~/.agents/skills/` | Reusable across agents and repositories; capability only. |
| codex-global | `~/.codex/skills/` | Reusable Codex-specific capability; `.system/` is product-managed. |
| managed | plugin/runtime cache | Versioned product or plugin capability; cache location grants no authority. |

Plugin namespaces make managed duplicates distinct. An unnamespaced duplicate
across shared-global and codex-global roots is a collision and must be resolved,
not selected by path order.

`kundur-round` has `allow_implicit_invocation: false` to prevent catalog-level
trigger inference outside this repository. The checked-in `AGENTS.md` bootstrap
is an explicit repository pointer, so every in-repository session still enters
it deterministically.

## Deterministic selection

1. Bootstrap `kundur-round`; it owns lane, round, evidence, feed, and manuscript
   scope.
2. If the user names `kundur-round`, load its checked-in `SKILL.md`. If the user
   uses a former project workflow name, treat it as an intent label and route
   through `kundur-round` to the corresponding internal module; never recreate
   a direct entrypoint. If the user names an external skill, use it as the
   primary method in scope.
3. Otherwise select at most one primary external skill, and only when its exact
   deliverable trigger matches and the scope manifest permits implicit use.
4. No exact match means no external skill. Handle the request directly.
5. `kundur-round` selects internal references only through
   `references/module-routing.md`. Required format handlers and external
   writing mechanics may support the primary method; they do not become
   co-owners or widen writes.
6. The project entrypoint and modules change only through a friction-backed
   repository task, with a forward test and normal code review. External skills
   change only through their pinned upstream/update process.

Conflict order: `kundur-round` and current user authorization always bound
project writes. Among external candidates only, explicit choice beats implicit
selection and an exact specialist beats a general router. Availability means
only discoverable, never selected or invoked.

## Project route

All research state, execution, evidence, manuscript, and submission work enters
through `kundur-round`. Its internal dispatch table is
`skills/kundur-round/references/module-routing.md`; those modules are not
skills. Broken-code and format/product tasks may use an exact external skill
under the current lane. `$ask-matt` remains explicit-only.

The project entrypoint and external academic skill inventory live in
`research-skills.scope.json`; repository mappings live only in
`skills/kundur-round/references/research-skill-adapter.md`. Validate the installed
placement, duplicates, and external policies with the strict checker in
`external-skills.md`.
