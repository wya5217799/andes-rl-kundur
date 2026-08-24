# R477 run flow and audit summary

- Registered training cells: 48 (8 arms x 6 seeds).
- Hash-verified carryovers: 16.
- Freshly trained cells: 32.
- Completed valid training cells: 48.
- Invalid training cells: 0.
- Incomplete or missing training cells: 0.
- Evaluation jobs: 16 (8 arms x half/final checkpoints).
- Complete stage-arm-seed-profile summaries: 384.
- Formal design/execution/integrity: VALID / COMPLETE / PASS.
- Formal verdict: MATERIAL-EFFECT-NOT-ESTABLISHED.
- Carryover allocation by actor source: N=16, P=0.
- Half/final marginal mean log effects: actor -0.141944004 / -0.024814075; critic 0.211829050 / 0.044168668.
- Curve-stability rule: for each actor/critic loss, compare median absolute values
  in the penultimate and final training deciles; require absolute log-ratio <=
  log(1.25). All 96 arm-seed-loss rows pass. This rule does not establish that
  the source-effect estimand itself plateaued.

The 16 carryovers all occupy actor-source N cells. Their hashes, factor identity,
43,200-step completeness, reward hash, base-state hash, and NTFS inode identity
pass the frozen reuse gate, but no same-round retraining comparison was performed.
Consequently, arithmetic replay is verified while a batch-by-actor-source effect
cannot be empirically excluded from this sealed dataset.

Generated only from SHA-256-verified R477 JSON artifacts. No training,
simulation, retuning, case exclusion, or endpoint change is performed here.
