# R402 causal-audit bundle import note

## Scope and authority

- Source: `C:\Users\27443\Downloads\r402_causal_audit_deliverables\r402_audit_package`.
- Imported for the fixed-title ICEMS 2026 manuscript
  *Decoupling-Oriented Coordination of Paralleled  VSGs With Multi-Agent Reinforcement Learning*.
- The unchanged source package is stored under `source/`. It is an external,
  non-authoritative causal review and calculation aid, not an experiment feed,
  registered claim, convergence certificate, DAE plant model, or new simulation.
- Project authority remains: final formal guards and manifests, current claims,
  same-line feeds, sealed results, then manuscript and external-review output.

## Integrity and local checks performed on 2026-08-16

1. All 25 imported files matched the supplied `SHA256SUMS`.
2. `python test_r402_tools.py` passed without installing new dependencies. The
   arithmetic tests reproduced 40 evaluation files, 216 learning trajectories,
   24 deterministic trajectories, and 240 trajectories in total.
3. The package input was checked against the R399, R402, R408, and R409 feeds,
   R402 formal manifest/analysis/endpoint table, the frozen cost and multiplier
   implementation, the retained manifests, and the existing read-only forensic
   dump.
4. The package correctly states that it did not receive project Jacobians and
   cannot turn its DAE/finite-horizon framework into plant evidence.

## Audit decision

**CONDITIONAL PASS as an advisory causal audit.** The package materially
improves the manuscript's failure interpretation and repairs one count error,
but it does not identify a unique failure mechanism or raise the empirical
claim ceiling.

### Verified or safely qualified for manuscript use

- The R402 physical evaluation comprises 40 JSON files containing 240
  trajectories: 216 learning trajectories and 24 deterministic trajectories.
  The formal manifest's `evaluation_records=240` outranks the erroneous
  `240 learning + 24 deterministic = 264` wording in the feed, current claim,
  evidence map, and former manuscript draft.
- The nine arm-seed training runs each completed 43,200 interaction steps and
  1,440 attempted episodes; these are per run, for 388,800 interaction steps
  and 12,960 attempted episodes in total.
- All 36 learning arm-seed-profile blocks fail both registered guard families,
  and the three learning arms degrade both registered endpoints relative to the
  deterministic reference. This remains a bounded CANARY-FAIL result.
- The CD-MATD3 costs contain no explicit action-magnitude, RMS, total-variation,
  or slew-use term, and the training costs are not identical to the registered
  endpoints and guards. This is a verified objective-to-decision-contract
  mismatch, not proof that the mismatch caused the observed degradation.
- Only the final 20 episode-level common costs and multiplier values are retained.
  Their multipliers are numerically small, touch zero, and finish positive. They
  cannot establish that the common term was deleted throughout training or that
  its actor-gradient contribution was negligible.
- `convergence_diagnostics_valid=true` means only valid budget completion without
  a registered nonfinite failure. It establishes neither convergence nor
  nonconvergence. Critic calibration, Bellman residuals, gradients, replay
  coverage, and complete chronological curves are unavailable.
- Message-enabled CD-MATD3 has no positive three-seed median increment over the
  matched no-message arm in this frozen bundle. The seedwise sign is
  heterogeneous, so the result does not establish that messages are intrinsically
  useless or harmful.
- R399 establishes nonzero finite-amplitude direct-M/D authority within its
  tested protocol. Residual learnable headroom and local conditioning remain
  unknown. R408/R409 establish a feasible joint target for a distinct energy-port
  object and cannot identify the direct-M/D action basis as the cause of R402.
- For an index-1 DAE, the imported formulas for reduced input/output maps and a
  lifted finite-horizon comparison are mathematically useful. Actual
  operating-point Jacobians, decoder branches, estimator states, and matched
  input metrics are still required before comparing plant authority.

### Claims that remain forbidden

- MARL cannot decouple paralleled VSGs, or all causal/finite-order controllers
  are infeasible.
- The common constraint was absent for all 1,440 episodes.
- CD-MATD3 failed to converge, or more training would necessarily fix it.
- Runtime messages are generally useless or harmful.
- Missing action-effort regularization, objective mismatch, decoder geometry,
  optimization, partial observability, credit assignment, or action-basis
  mismatch is the sole or dominant cause.
- The energy-port result proves why R402 failed or may be pooled numerically with
  the direct-M/D experiment.
- The actual ANDES DAE has a zero or nonzero reduced direct-M/D input Jacobian;
  the needed matrices have not been extracted.

## Manuscript disposition

The manuscript may use the corrected count, the objective/gate mismatch as a
design fact, the retained-log limitations, and the unresolved competing-cause
interpretation. It must replace wording that ranks action/interface alignment
above optimization or learning complexity. The conference draft needs no new
training to report R402 safely.

The smallest future discriminating evidence is either (1) an actual matched
DAE/finite-horizon authority calculation for direct-M/D and energy-port objects,
or (2) a fresh, preregistered single-factor successor experiment with complete
critic, gradient, multiplier, replay, and message-intervention logging. Both are
future work and are not authorized by the current manuscript-only stage.

## Outstanding repository correction

The R402 feed and `CLM-1155` still contain the superseded 264-count wording, and
`formal_analysis.json#/round` says `R401` while the manifest says `R402`;
`formal_execution.json` is absent. These are provenance/reporting defects, not
identified policy-failure causes. They require a project-native correction
record or immutable sidecar before submission; sealed artifacts must not be
silently rewritten.
