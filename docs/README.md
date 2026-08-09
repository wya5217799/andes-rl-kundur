# Documentation homes

Each durable document family has one home. Delivery-specific content follows
the registered delivery line in `docs/repo-hygiene/contract.json`.

| Family | Durable home | Rule |
|---|---|---|
| Architecture decision | `docs/adr/` | One numbered ADR per accepted decision |
| Agent integration | `docs/agents/` | Tracker, label, and domain-doc consumer rules |
| Engineering note | `docs/eng-notes/` | Simulator and implementation knowledge |
| Cross-line research investigation | `docs/research/` | Dated landscape, audit, or strategy report |
| Repository governance | `docs/repo-hygiene/` | Contract, baseline, lifecycle, type-check scope, external-skill adapters, and evidence snapshots |
| Project foundation learning | `learning/README.md` | Non-authoritative Foundation Atoms, prerequisite edges, project-use links, and repository anchors |
| Line-specific deep research or decision | `paper/<line>/` | Register in that line's `ARTIFACTS.json`; do not place it in another paper line |
| Delivery evidence report | `paper/<line>/reports/` | Feed contract from `kundur-round` |
| Delivery draft/corpus | Registered delivery root | Roles declared by the delivery registry |
| Review working notes | `tmp/<line>/` | Ephemeral by default; persist only one registered consolidated review when needed |
| Work specification and ticket | GitHub Issues | Tracker rules in `docs/agents/issue-tracker.md` |

Historical implementation plans already under `docs/superpowers/plans/` or
`quality_reports/plans/` remain archived evidence. New work is specified and
split in GitHub Issues instead of creating another plan directory.

Generated status lives in `memory/STATE.md`. Stable navigation documents point
there rather than copying the latest round, counts, or headline numbers.

## Growth budget

One experiment may add durable prose only to its plan, one feed, one claim
card, and one verdict. Pre-draft academic review is summarized in the feed's
publication gate; detailed review stays in the conversation or `tmp/` unless
it becomes an existing durable type such as a question, correction, ADR,
issue, updated literature matrix, or registered manuscript artifact.
`repo_health.py` enforces the round-directory half of this budget from R287
onward; historical round files remain untouched.

New conversations run `memory/tools/session_context.py` and read at most eight
selected files. The ledger and historical documents may grow without growing
the default context window.

## Generated-document lifecycle

Every active manuscript line owns one `ARTIFACTS.json`. A durable generated
document must declare a stable id, purpose, path, status, producer, inputs, and
whether it is authoritative or only a derivative view. Time-sensitive
research, journal decisions, and policy audits also declare `review_after`.

- Default output is ephemeral and stays in `tmp/<line>/`.
- Promote an output only when another session must rely on it.
- Keep one active canonical artifact per purpose.
- Replace with `supersedes`; do not maintain parallel "final-v2-new" files.
- Input-hash mismatch or an expired `review_after` makes a derivative artifact
  stale until refreshed.
- Feed, claims, verdicts, and raw results keep their existing authority; a
  generated report never becomes a second evidence ledger.
