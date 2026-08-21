# Owner decision: soft-spot experiment program becomes the line's top future priority (2026-08-16)

## Decision

The repository owner directed in the 2026-08-16 session: (1) keep the
fixed-connectivity modified-Kundur topology as the primary platform because
it is the canonical two-area inter-area benchmark; topology variation, not a
bigger grid, is the accepted way to probe robustness, because larger grids
would slow the already-costly 60-Hz phasor simulation further; (2) resolve
all remaining experimental soft spots, with the soft-spot program registered
as the most important content of future experiments on this line; (3) a
follow-up long task will execute the program incrementally, using the full
host capacity as in R410. This registers that decision and the program
registry (`working/soft_spot_experiment_program.md`) as the line's forward
work anchor.

## Scope of the authorized program

- Each program item that requires new physical execution opens its own
  evidence round on this line, in program order, one active round at a time
  (reserve -> plan -> preflight -> capacity -> rehearsal -> seal -> execute
  -> feed -> claim -> gate -> close), reusing the R410 execution pattern.
- Eval-only items run first and may be shard-parallelized inside each
  round's frozen budget; training items follow the 4-worker capacity-ladder
  pattern.
- The ICEMS 2026 submission path outranks the program: after 2026-08-28
  registration, only results that complete their full lifecycle before the
  2026-09-07 final-paper freeze may enter the manuscript; all other results
  feed the post-conference extension and must stay out of the paper.

## Authority boundaries

- No title change; no algorithm-dimension sweep (R86 plateau,
  CLM-0148/0149); no cross-simulator 1:1 chase (ADR-0005); no
  bigger-than-Kundur grids (owner constraint).
- The R410-sealed runner, learner, and results remain frozen evidence;
  program items that touch the learner need new rounds with their own
  seals and pre-registered single-factor contracts.
- Topology-variant rounds must pass the registered topology/EIG hard gate
  (CLM-0665): line outages only through `apply_line_outage()` / ANDES
  `Model.set`, and paper-facing EIG requires `TDS.test_ok`, `exit_code=0`,
  initialization residuals, finite spectrum, and the positive-real guard.

## Records

- Decision doc: this file
- Program registry:
  `paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md`
- Future rounds: R411+ reserved by the atomic tool when each item starts
