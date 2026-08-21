# Active-round resume contract

Use this bounded card only when `session_context.py` reports `resume-round`.
The active `plan.md` is the frozen authority for the experiment. This card
routes execution; it does not replace the full `kundur-round` skill.

1. Read `CLAUDE.md`, this card, and every active round plan returned by
   `session_context.py`. Do not load historical ledgers unless a plan points
   to them. Rounds without `formal_seal.json` are parked: the context lists
   them in `active_rounds` but keeps their plans out of the cold-start byte
   budget; read a parked plan lazily right before its capacity/prepare step.
2. Run `round_preflight.py <round>` before the first paper-facing execution.
   Preserve the plan, seal, inputs, outputs, sidecars, failures, and exclusions.
   Never overwrite a formal artifact or change a threshold after seeing an
   endpoint.
3. Execute only the active plan for the selected manuscript line. Do not
   reserve another round on that line, broaden the question, enter manuscript
   prose, or bind evidence to a paper line unless the plan explicitly
   authorizes it. Exception: the owner's standing concurrency authority
   (CLAUDE.md 并行预算) allows same-line concurrent rounds whenever the
   concurrent-load ladder and total-memory accounting show hardware surplus;
   the new round's plan must declare every in-flight round's processes via
   `other_reserved_processes`. A separately selected task may own one round
   on a different manuscript line; a repository-global round still blocks
   every line.
4. Before feed numeric claims, reserve a claim atomically. The feed is the
   compact experiment-facing fact sheet; large analysis, Deep Research, and
   raw outputs remain authoritative targets reached by pointers.
5. At publication and close-out time, lazily read `../SKILL.md` and the
   references it routes to. Run the evidence and domain gates on the feed,
   finalize the same-round claim card to the allowed wording and bind it back
   to the feed, then run `feed_check.py`, verdict/question/programme updates,
   `close_round.py`, `validate.py`, `render.py`, governance checks, and relevant
   tests. Copy the verdict's `## 给 PI 的话` verbatim into the handoff.
6. If a retained failure or integrity violation appears, stop and diagnose it.
   Do not delete, hide, or retry that artifact unless the frozen plan already
   defines a recovery path.

The next session discovers the current state through
`python memory/tools/session_context.py --json --line <line-id>` when a paper
is named; no chat transcript is an authority.
