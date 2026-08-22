---
round: R473
state: active
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-23'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R473 plan — U2 successor: complete the paused factorial from the frozen 96-shard inventory

**Opened**: 2026-08-23
**Driver**: The owner ordered a shutdown while R472 had 96/108 valid training shards; the successor completes the 12 missing cells and runs the full evaluation/aggregate under frozen R472 semantics, with the 2026-08-22 source-confound wording boundary.
**Parent**: R472 aborted (owner-ordered shutdown); R470/R471 engineering aborts; CLM-1315/R431, CLM-1360/R438, CLM-1440/R460; guardrails `skills/kundur-round/references/experiment-design-guardrails.md` §A/E.

## TL;DR

Reuse the 96 complete R472 training shards via NTFS hardlinks after a frozen-inventory audit, train only the 12 missing `an_cn_r0`/`an_cn_r1` cells, then evaluate all 108 half/final checkpoints and aggregate under the byte-identical R472 protocol. Scientific semantics, endpoints, thresholds, and the four-way gate are unchanged; the verdict wording carries the 2026-08-22 boundary (total source effect, never pure semantic neighbour value).

## Snapshot at plan-time (oracle as of 2026-08-23)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program (shared action variables per non-anticipative info class, solution section 5.4) certify or refute INFORMATION-LIMITED for the 2% joint target under the exact R352/R353 observation histories?

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?

## Methodology

### Frozen evidence identity

- Work class: **evidence**; create-only root
  `results/research_loop/r473_u2_source_factorial`.
- Design is R472 byte-for-byte: 18 `(actor source in {0,P,N}, critic source in
  {0,P,N}, reward in {0,1})` cells by seeds `401..406`, 43,200 physical
  training steps, 24 development and 24 held-out scenarios, half/final
  checkpoints, full curves. Primary/secondary endpoints, 10% log materiality,
  exact sign flips, paired bootstrap, Holm alpha .05, and optimization gates
  are inherited unchanged.
- U3 semantics unchanged: previous executed action in state; raw and executed
  actions retained; current/target/actor Q paths consume projected actions;
  raw-policy entropy only. Network, optimizer, replay/update count, reward,
  action limits, environment, and seeds do not change.

### Immutable reuse gate

- Frozen candidate list: `tmp/yang_md_decoupling_marl/r472_shutdown_inventory_20260822.json`
  (+ `.sha256`): 96 complete shards = every cell except
  `an_cn_r0` and `an_cn_r1` (all six seeds each).
- Reuse a R472 shard iff the shutdown inventory marks it complete AND an
  on-disk re-verification passes: manifest hashed, `valid=true`,
  `interaction_steps=43200`, all ordinary files have matching sidecars, both
  half/final checkpoints and full curves exist, and arm/seed is unique.
  Any count or hash drift blocks seal.
- Reuse all six R472 donor/base bundles only after independently verifying
  split tensors, base states, manifests, sidecars, donor marginal audits, and
  registered scenario shapes. No donor regeneration.
- After seal, import valid files into R473 as NTFS hardlinks and record source
  path, source hash, file identity, and byte count in an import provenance
  manifest. Hardlinks add no second data bytes.

### Missing cells and inference

- Freshly trained in R473: exactly `an_cn_r0` and `an_cn_r1`, seeds 401–406
  (12 shards). The 96 reused cells are not re-run.
- `N`: true same-time ring neighbours; `0`: zero slots 3:7; `P`: independent
  scenario-matched donor with `pi(e)=1-e`, nodes `i` and `i+2` (unchanged
  from the frozen design — see Theory intake for the wording boundary).
- Power remains `n=6` from sealed R431 paired log-ratio `sd=0.0823901083` and
  materiality `log(1.10)`. `OPTIMIZATION-UNRESOLVED` applies on failed/missing
  seed, half/final direction flip, or absent late stabilization.

### Evaluation, aggregate, hardware, durable launch

- After the 12 new shards: verify all 108 training manifests, run the 36
  evaluation shards over every half/final checkpoint, then the R472 aggregate
  protocol and final manifest.
- Fresh capacity ladder post-reboot (rungs 1/2/4/8/12/16, representative task
  count >=32 per rung, marginal-throughput noise rule), then freeze 16
  workers + 1 launcher, one native thread each, host budget 17, no reserved
  load.
- Formal training/evaluation launches via hidden `Start-Process wsl.exe` with
  stdout/stderr redirected under `tmp/andes/r473_detached_*`. A nonzero phase
  stops the pipeline. No retry in R473; any post-seal scientific or
  orchestration failure requires another successor. Do not inspect R472
  endpoint values before aggregation (structure only: validity, steps,
  identities, hashes).

## Formal launch contract

- `formal_entry`: `scripts/run_r473_u2_source_factorial.py <phase>`
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r473_u2_source_factorial.py rehearse`
- `rehearsal_scope`: `sac_semantics_probe`, objective/reward identities,
  donor/reuse audit against the frozen shutdown inventory, hardlink identity
  probe in scratch, terminal truth table, initialization parity, and real
  three-step ANDES update; no formal root.
- `capacity_evidence`: `memory/rounds/R473/capacity_evidence.json`
- `wsl_python_processes`: 17
- `native_threads_per_process`: 1
- `host_process_budget`: 17
- `other_reserved_processes`: 0

## Gate

- `U2-SOURCE-EFFECT-SUPPORTED`: all integrity/optimization/reuse gates pass and
  at least one Holm-controlled primary `N-P` effect has CI lower bound above
  `log(1.10)` in the beneficial direction.
- `U2-SOURCE-EFFECT-NOT-SUPPORTED`: all gates pass but neither effect clears
  materiality and multiplicity.
- `OPTIMIZATION-UNRESOLVED`: failed/missing seed, budget-direction flip, or
  absent stabilization.
- `FACTORIAL-INVALID`: any import identity, initialization, donor, reward,
  executed-action, budget, evaluation, or hash gate fails.
- Wording boundary (code-verified 2026-08-22, guardrails §A): under any
  outcome, a positive `N-P` effect is worded as the total algorithm effect of
  the authentic neighbour source versus the exogenous random-policy donor
  placebo at fixed other factors — never a pure semantic neighbour-information
  value. No outcome authorizes a universal intrinsic communication claim.

## Theory intake

- Retained prediction (inherited R472): `N` improves held-out primary loss
  over marginal-matched `P` by more than 10% for at least one role without a
  half/final direction flip.
  - observable: per-seed paired log-loss contrasts `N-P` at fixed
    critic/reward factors (definition, source, and threshold inherited from
    the R472 aggregate contract); half/final direction consistency; late-curve
    stabilization; Holm result; CI lower bound vs `log(1.10)`.
  - verdicts: `supported` / `refuted` / `undecidable` written back in the feed.
- Boundary (external intake 2026-08-22, confirmed against
  `scripts/run_r470_u2_source_factorial.py::{source_rows,generate_donor_and_base,donor_marginal_audit}`):
  P rows read the exogenous random-policy donor bank while N rows read the
  contemporaneous controlled trajectory; the donor audit is donor-internal.
  This is a wording constraint, not a measurement: even `SUPPORTED` is
  reported as the confounded total source effect.
- Blocked: intrinsic/topology-general communication value and any partial
  R472 endpoint interpretation.

## 资产保护契约

Preserve R431/R438/R451/R460/R470/R471/R472 and imported GPT material
byte-for-byte. Add only the R473 adapter/test, reuse audit against the frozen
shutdown inventory, hardlink-based result root, the 12 missing training
shards, evaluation/aggregate results, analysis/report/claim/verdict, and final
package. Do not inspect R472 endpoint outcomes before R473 aggregation; only
validity, steps, identities, and hashes may gate reuse.

## Cross-references

- R472 shutdown inventory:
  `tmp/yang_md_decoupling_marl/r472_shutdown_inventory_20260822.json`
- CLM-1315: endpoint and paired-seed definitions.
- CLM-1360: same-learner 16-worker capacity.
- CLM-1440: executed-action Bellman semantics.
- Guardrails: `skills/kundur-round/references/experiment-design-guardrails.md` §A/E.
