# Successor design amendment after the R402 canary failure

## Decision

The repository owner reviewed the R402 canary result and the forensics
memorandum and decided to **continue optimizing the algorithm** rather than
close the line.  The R400 stop remains valid for the frozen CD-MATD3 bundle
as executed; this amendment registers a materially repaired successor design
inside the same learner family (memoryless CD-MATD3, four independently
executed actors, twin joint critic).  No algorithm-family replacement is
authorized; the fixed title, the Yang-compatible four-VSG direct-M/D object,
the three-arm message attribution, and the Gate A/B decision logic remain
prospective and unchanged.

The successor work proceeds **small and fast**: every design change is first
validated as a scratch iteration on the already-disclosed development
profiles with tiny budgets (minutes per run), and only a design that passes
its scratch acceptance enters a prospectively frozen evidence canary on a
fresh unseen bank with fresh seeds.

## Design repairs (frozen from the R402 forensics)

1. **Remove the Lagrangian dead zone.** The adaptive dual is deleted; the
   actor objective becomes a fixed-weight combination
   `-(Q_differential + w_c * Q_common)` with `w_c = 1.0`.
2. **Add an action-effort term.** The differential reward channel becomes
   `r_d = -(c_d + w_a * mean_i ||a_i||^2)` with `w_a = 1.0`; the common
   channel is unchanged (`r_c = -c_c`).
3. **Full diagnostic storage.** Every training run records per-episode
   returns, per-channel costs, critic losses, and action statistics for
   convergence auditing; no last-20 truncation.
4. **Message attribution unchanged.** The three arms stay; the message
   question remains the object of study.
5. **Fresh bank and fresh seeds are mandatory** for the successor canary;
   the R402 profiles are disclosed and burned as unseen evidence.

## Scratch acceptance for the repaired design (small-fast loop)

Before any evidence freeze, a scratch iteration on the four disclosed
development profiles (tiny budget, e.g. 1200 interaction steps, both CD
arms) must show all of:

- final common-multiplier-independent behavior: per-step action magnitude
  mean below the R402 message-arm level and slew-bound hit fraction below
  5%;
- common cost per episode no worse than 1.5x the deterministic reference on
  the same profiles;
- differential cost not worse than the R402 message-arm baseline on the same
  profiles;
- finite diagnostics everywhere.

These scratch acceptance numbers are development-checkpoints only, not
evidence, and may be tightened or replaced by the successor canary round's
own prospectively frozen contract.

## Successor evidence route

- The successor evidence round freezes a fresh development/evaluation bank
  (disjoint from R399 and R402), fresh seeds, the repaired reward contract,
  the same 43200-step budget, and the same Gate A decision tree, then
  executes the three arms exactly as R402 did.
- A canary PASS still authorizes only a separately sealed Gate B; a FAIL
  again ends the learner route without algorithm replacement.
- No sweep: `w_c` and `w_a` are frozen at 1.0 here; tuning them
  post-hoc is outside this amendment.

## Execution boundary

This amendment writes decision, navigation, and scratch-prototype assets
only.  It runs no ANDES evidence, trains no evidence policy, and opens no
unseen bank.  The successor canary requires its own prospectively reserved
round and preflight.
