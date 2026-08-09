# Codex research bootstrap

完整工程规则在 `CLAUDE.md`——文件名是历史遗留,与 Claude Code 工具无关;
它是本仓库工程规则唯一真源。改代码或仓库治理前必读。

This repository is a TPWRS-oriented automatic research programme, not an
open-ended algorithm sweep.

## Repository learning

When the user asks to understand the foundations behind this repository, use
the available `atomic-stem-tutor` Repository mode and maintain the registry
described in `learning/README.md`.
Load only the relevant branch, enrich one bounded prerequisite slice, and run
the bundled project-registry validator. Ordinary implementation does not
trigger this path. `learning/` is non-authoritative: it never replaces source,
feeds, claims, verdicts, or manuscript evidence. Ordinary Chat atoms enter it
only through an explicit repository import followed by source revalidation.

At the start of every research session:

1. If the request clearly names one manuscript, run
   `python memory/tools/session_context.py --json --line <line-id>`. Use
   `python memory/tools/session_context.py --json --list-lines` first when the
   repository line id is unknown. Otherwise run
   `python memory/tools/session_context.py --json` and accept its fallback
   route.
2. Read every path in its bounded `required_reading` list and no historical
   ledger files unless the current task requires them.
3. If it reports `resume-round`, close that round before reserving another on
   the same manuscript line. A separately selected manuscript line may own one
   different active round; an unowned/global active round still blocks every
   line. If it reports `research`, use its exact objective, verification, and stopping
   conditions. If it reports `manuscript`, follow the active `LINE.md`. If it
   reports `manuscript-refresh`, clear the artifact freshness alerts before
   drafting or reviewing. If it reports `idle`, do not manufacture an
   experiment.
4. Read `CLAUDE.md` before changing code or repository governance, even when it
   is not part of a manuscript-only reading set.
5. Before reserving a round, classify the work as `scratch`, `manuscript`, or `evidence`
   using `skills/kundur-round/SKILL.md` section 2. Offline implementation and
   development-data prototypes stay in `scratch`; any new physical execution,
   protected-asset change, or claim/question/title consequence enters
   `evidence` prospectively.
6. Reserve round and claim IDs only through the atomic tools documented in
   `CLAUDE.md`. Manuscript evidence rounds use
   `reserve_round.py --strict-no-active --line <line-id> --write-plan-stub`,
   which records line ownership and rejects a second active round on that
   line. Preflight before running ANDES or training.
7. Finish every paper-facing experiment with a feed publication gate before
   claim registration and drafting. Then complete the verdict, measured
   provenance, question/claim updates, reconcile the active manuscript
   `LINE.md`/`ARTIFACTS.json` navigation snapshot, run
   `repo_health.py check --no-baseline`, `validate.py`, `render.py`, tests,
   and the verbatim `## 给 PI 的话`.
   From R317 onward that chat delivery is a separate plain-Chinese layer with
   exactly three parts: what happened, what it means, and what happens next.
   It contains no English abbreviation, repository identifier, filename,
   code name, or specialist term. Exact terminology, metrics, identifiers,
   and data remain in the feed, claim, results, and technical verdict
   skeleton. Do not add a technical recap to the user-facing closing report
   unless the user explicitly asks for it.
8. When a global research, writing, or manuscript-review skill is used, apply
   `skills/kundur-round/references/research-skill-adapter.md`. Global skills
   advise or verify; they never own project or manuscript-line state.

Each active manuscript has its own `paper/<line>/LINE.md` and
`ARTIFACTS.json`. The selected line's declared write scope is exclusive:
another paper may be read as a source, but is not writable without separately
selecting and authorizing that line.
`active` is a manuscript lifecycle state, not a global lock: several ongoing
papers may remain active, `--line` selects the current session, and `priority`
is only the fallback when the request does not identify a paper. Switching
lines never copies evidence or changes another line's lifecycle state.
Round ownership follows the same scope: at most one active evidence round per
manuscript line. Repository-global rounds and protected shared-asset changes
remain exclusive. Formal simulation concurrency has no fixed repository
number; each new evidence round must freeze a performance-derived whole-host
budget and subtract capacity reserved by other executing lines.
`LINE.md` is navigation only: use `decision_refs` and claim-to-feed
`evidence_refs`; never copy Deep Research conclusions, feed facts, or result
values into it, and never eagerly list authoritative feeds in
`required_reading`.

Research priority:

`correctness and objective validity -> residual mechanism -> topology
generalisation -> safety/stability -> cross-simulator/HIL -> manuscript`.

Do not restart algorithm-only SOTA hunting on the fixed Kundur topology.
Historical checkpoints affected by the R261 recurrent-target defect are legacy
evidence, not corrected-algorithm evidence.
