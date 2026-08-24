# Internal module routing

`skills/kundur-round/SKILL.md` is the repository's only skill entrypoint. Files
in this directory are internal references: they have no skill frontmatter, are
not selected from the skill catalog, and acquire no authority of their own.

## Dispatch

After the session bootstrap and lane decision, classify the immediate object
and decision. Load only the matching module, read it completely, execute its
bounded return, then return control to `kundur-round`.

| Exact trigger | Load | Required input | Bounded return |
|---|---|---|---|
| The next research decision or owner is genuinely ambiguous | `research-junction.md` | Live object, one decision, authority, current owner | One route card; no lane or write authorization |
| A non-quick launch, capacity change, ETA, or active-run monitoring decision is due | `execution-readiness.md`; add `formal-execution.md` for sealed/frozen work | Owning plan, run state, measurements, budgets | `RUN-READY`, `MEASURE-FIRST`, or `HOLD` card |
| A canonical feed or frozen manuscript claim set needs evidence binding | `evidence-audit.md` | Canonical feed or frozen draft plus authoritative evidence | Claim-evidence audit |
| The same frozen input needs power-system physics, units, experiment, statistics, or scope review | `power-systems-audit.md` | Same input used by the evidence audit | Domain audit |
| A target venue, article type, and concrete package are all fixed | `submission-audit.md` | Frozen package and fresh official venue rules | Mechanical compliance audit |
| The user authorizes workflow repair after one severe failure or a repeated friction pattern | `skill-maintenance-loop.md` | Reproducible behavior, expected result, affected local source | Smallest repair plus forward test |

`publication-gate.md` fixes the evidence-audit then domain-audit sequence on the
same canonical feed. The manuscript route may repeat those modules on one
frozen draft. Submission audit is later and cannot substitute for either.

## Collision rules

- Bootstrap, lane, round lifecycle, feed, claim, manuscript-line state, and
  write scope always stay in `kundur-round`.
- Research junction recommends one route only. It never invokes another project
  skill because no other project skill exists.
- Execution readiness owns capacity and launch mechanics, not scientific
  question, comparator, thresholds, or claim strength.
- Evidence audit owns traceability. Power-system audit owns domain validity.
  They may both return blockers, but neither rewrites the other result.
- Submission audit owns current venue mechanics only. Venue choice, scientific
  merit, and evidence sufficiency remain upstream decisions.
- Maintenance owns workflow code and tests only. It never modifies research
  evidence to make a workflow check pass.
- Historical artifact `producer` values using former skill names are immutable
  provenance labels, not callable entrypoints.

## External skills

If an exact external deliverable is needed, return to
`docs/repo-hygiene/skill-routing.md`. Select at most one primary external skill;
apply `research-skill-adapter.md`; never let a reference module nested-route or
grant project writes.
