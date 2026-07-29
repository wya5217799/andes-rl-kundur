# Documentation homes

Each durable document family has one home. Delivery-specific content follows
the registered delivery line in `docs/repo-hygiene/contract.json`.

| Family | Durable home | Rule |
|---|---|---|
| Architecture decision | `docs/adr/` | One numbered ADR per accepted decision |
| Agent integration | `docs/agents/` | Tracker, label, and domain-doc consumer rules |
| Engineering note | `docs/eng-notes/` | Simulator and implementation knowledge |
| Cross-line research investigation | `docs/research/` | Dated landscape, audit, or strategy report |
| Repository governance | `docs/repo-hygiene/` | Contract, baseline, lifecycle, external-skill adapters, and evidence snapshots |
| Delivery evidence report | `paper/<line>/reports/` | Feed contract from `kundur-round` |
| Delivery draft/corpus | Registered delivery root | Roles declared by the delivery registry |
| Work specification and ticket | GitHub Issues | Tracker rules in `docs/agents/issue-tracker.md` |

Historical implementation plans already under `docs/superpowers/plans/` or
`quality_reports/plans/` remain archived evidence. New work is specified and
split in GitHub Issues instead of creating another plan directory.

Generated status lives in `memory/STATE.md`. Stable navigation documents point
there rather than copying the latest round, counts, or headline numbers.
