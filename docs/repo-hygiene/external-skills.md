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

The suite is installed globally at
`$CODEX_HOME/skills/academic-research-suite`, outside this repository. Its
pinned sources, commits, license, adapter version, manifest hash, and update
method are recorded in `docs/repo-hygiene/external-skills.lock.json`.

The exact snapshot removed from the repository is recoverable from Git commit
`54ab40b` and from the verified global installation. Updating it requires
rebuilding from the pinned upstream sources, verifying the manifest hash, and
changing the lock in the same review.
