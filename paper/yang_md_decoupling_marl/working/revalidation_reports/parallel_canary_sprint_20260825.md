# Yang M/D old-conclusion revalidation — parallel canary sprint

> Governance status: quarantined development-visible scratch diagnostics.
> These physical jobs were outside the repair3 allowlist and are excluded
> from every formal seal, claim, manuscript number, and route verdict.

## Scope and authority

This sprint covers only the Yang M/D decoupling manuscript line. It ran one
corrected semantic gate, the 12-trajectory direct-M/D route canary, and the
20-trajectory energy-port held-out canary. The jobs were accelerated in
scratch at the owner's request. They are diagnostic routing evidence, not
formal manuscript evidence; no training or paper number was changed.

The concurrently completed capacity artifact
`capacity_r478_zero_action_repair1.json` (SHA-256
`2366b265c8b98b86aa329aa06378af09b417a95dc7427d2888c5174777dcfb7f`)
is quarantined as non-authoritative. Other WSL jobs added host load during the
ladder, and the reviewed runner now also requires post-ladder identity binding.
It must never set a formal worker count or ETA.

## Frozen scratch outputs

- semantic output-set hash: `ac063d300087fbe33c230bfb0c1c8c281a8e62e11d9d34e91805bd58b6f6083e`
- direct-M/D 12-record output-set hash: `8314956b641105da638285bd315b3137f6a88dad7e47eedca1e44b00e271018d`
- energy-port 20-record output-set hash: `8386b57d371e1a6dbf290efa0041fff31decbba4b6beaaf1f51efdddff247664`
- raw logs: `tmp/andes/r478_parallel_canary_scratch/`

Each output-set hash is SHA-256 over sorted `filename`, NUL, per-file SHA-256,
and newline records.

## Gate 1 — corrected semantic object

Classification: `SEMANTIC-GATE-PASS`.

All registered checks passed: two zero-action disturbances; zero-action M/D
equal to the frozen parameter card; one bounded nonzero action with exactly
five substeps; independently calculated card targets equal reported targets,
applied values, and converted runtime readback; and both resets restore the
frozen card after an intervening runtime perturbation.

Old-conclusion assessment: the corrected M/D object is operationally coherent.
This does not validate any old numerical performance conclusion.

Decision: **retain old route** at the base-semantics level.

## Gate 2A — direct-M/D canary

Classification: `ANALYSIS-INVALID`.

All 12 registered `dev_a` trajectories completed, but both arm summaries fail
the actuator mapping check. The old R416 execution loop stores raw
system-base `GENCLS.M/D` values in fields that the corrected estimator interprets
as device-base telemetry. This is an instrumentation-boundary mismatch, not a
controller-performance verdict.

Old-conclusion assessment: no direct-M/D comparator, MARL failure, source
factor, or guard-count conclusion can yet be transported to the corrected
object.

Decision: **redesign successor instrumentation only**. Do not redesign the
controller or learner yet. The next valid direct canary must record device-base
`info[M_es/D_es]` or explicitly convert runtime readback before classification.

## Gate 2B — energy-port held-out canary

Classification: `HELDOUT-FAIL` (diagnostic scratch; run speculatively before a
valid 2A result and therefore not formal route authority).

- differential ratio: `0.9995399761` (registered ceiling `0.95`)
- probe cross-ratio: `1.0107425680` (registered ceiling `1.10`)
- guards: all pass
- candidate/local differential energies: `0.000183636999` /
  `0.000183721515`

The old manuscript value near `0.938218` does not survive this corrected-object
scratch bank. The constructive energy-port claim is therefore potentially
changed even though its guards remain clean.

Decision: **do not continue the old energy-port topology, extra-condition, or
residual-learning task queue**. First confirm this single held-out failure in a
sealed successor. If confirmed, remove or rewrite the old positive companion
claim instead of spending hardware on downstream old tasks.

## One next task

Create a successor authority generation that preserves the invalid repair-1
capacity artifact, fixes the direct-M/D telemetry boundary, re-runs only the
12-trajectory direct canary with a stable pre/post source identity, and emits a
create-only report. Training, the 224-job source factorial, full topology banks,
and formal manuscript-number replacement remain closed.

## Post-run governance audit

All physical canaries in this sprint are quarantined diagnostics because they
were not listed in the repair3 allowlist. Their numbers may motivate a
prospective successor but cannot close the frozen energy-port branch or open a
direct formal bank. The viewed `eval_*` identities cannot be reused as formal
holdouts.
