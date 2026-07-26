# Codex research bootstrap

This repository is a TPWRS-oriented automatic research programme, not an
open-ended algorithm sweep.

At the start of every research session:

1. Read `memory/RESEARCH_PROGRAM.md`, `memory/STATE.md`, and `CLAUDE.md`.
2. Run `python memory/tools/research_goal.py --json`.
3. If it reports an active round, resume and close that round before reserving
   another one.
4. If it reports a ready goal, use its exact objective, required reading,
   scope limits, verification, and stopping conditions.  The user's standing
   request to continue the TPWRS automatic research programme authorizes a
   stage goal for that selected work.
5. Reserve round and claim IDs only through the atomic tools documented in
   `CLAUDE.md`; preflight before running ANDES or training.
6. Finish every experiment with a verdict, measured provenance, question/claim
   updates, `validate.py`, `render.py`, and the verbatim `## 给 PI 的话`.

Research priority:

`correctness and objective validity -> residual mechanism -> topology
generalisation -> safety/stability -> cross-simulator/HIL -> manuscript`.

Do not restart algorithm-only SOTA hunting on the fixed Kundur topology.
Historical checkpoints affected by the R261 recurrent-target defect are legacy
evidence, not corrected-algorithm evidence.
