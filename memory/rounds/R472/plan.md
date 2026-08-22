---
round: R472
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-23'
supersedes_rounds: []
superseded_by_round: null
abort_reason: owner-ordered shutdown to power off the host at 96/108 valid shards;
  successor round reuses the frozen inventory
superseded_note: null
---
# R472 plan — U2 detached-orchestration successor with immutable shard reuse

**Opened**: 2026-08-21
**Driver**: Complete U2 without duplicating 16 valid R471 training shards after the external session ceiling interrupted only the launcher.
**Parent**: R470/R471 engineering aborts; CLM-1315/R431, CLM-1360/R438, CLM-1440/R460.

## TL;DR

Reuse only R471's six complete donor/base bundles and 16 fully completed,
hashed 43,200-step training shards; exclude every half-only shard. Run the 92
missing factorial cells, then evaluate all 108 half/final checkpoints under one
R472 aggregate. Scientific semantics are unchanged. The sole operational
change is a detached Windows-hidden WSL launcher that survives task turns.

## Snapshot at plan-time (oracle as of 2026-08-21)

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
  `results/research_loop/r472_u2_source_factorial`.
- Full design remains 18 `(actor source in {0,P,N}, critic source in {0,P,N},
  reward in {0,1})` cells by seeds `401..406`, 43,200 physical training steps,
  24 development and 24 held-out scenarios, half/final checkpoints, and full
  curves. Primary/secondary endpoints, 10% log materiality, exact sign flips,
  paired bootstrap, Holm alpha .05, and optimization gates are byte-for-byte
  inherited from R471.
- U3 semantics remain: previous executed action in state; raw and executed
  actions retained; current/target/actor Q paths consume projected actions;
  raw-policy entropy only. Network, optimizer, replay/update count, reward,
  action limits, environment, and seeds do not change.

### Immutable reuse gate

- Before any R472 network construction, create
  `memory/rounds/R472/reuse_audit.json`. Reuse a R471 training shard iff its
  manifest is hashed, `valid=true`, `interaction_steps=43200`, all ordinary
  files have matching sidecars, both half/final checkpoints and full curves
  exist, its donor/base hashes match the seed's R471 donor manifest, and its
  arm/seed is unique.
- Expected frozen reuse set: all six seeds of `a0_c0_r0`, all six of
  `a0_c0_r1`, and seeds 401--404 of `a0_cp_r0` (16 shards). Any count or hash
  drift blocks seal. The 16 R471 half-only directories are explicitly excluded.
- Reuse all six R471 donor/base bundles only after independently verifying both
  split tensors, base states, manifests, sidecars, donor marginal audits, and
  registered scenario shapes. No donor regeneration.
- After seal, import valid files into R472 as NTFS hardlinks and record source
  path, source hash, file identity, and byte count in an import provenance
  manifest. Hardlinks add no second data bytes. Missing 92 shards are freshly
  created in R472; no completed job is duplicated.

### Source intervention and inference

- `N`: true same-time ring neighbours; `0`: zero slots 3:7; `P`: independent
  scenario-matched donor with `pi(e)=1-e`, nodes `i` and `i+2`. Preserve exact
  no-fixed-point, non-neighbour, tuple-change, and per-slot/feature/time pooled-
  marginal hashes.
- Power remains `n=6` from sealed R431 paired log-ratio `sd=0.0823901083` and
  materiality `log(1.10)`. `OPTIMIZATION-UNRESOLVED` applies on failed/missing
  seed, half/final direction flip, or absent late stabilization.

### Hardware and durable launch

- Recheck current WSL load and R438 capacity; freeze 16 unique workers plus one
  launcher, one native thread each, host Python budget 17, no reserved load.
- Formal training launches via hidden `Start-Process wsl.exe` with stdout/stderr
  redirected under `tmp/andes/r472_detached_*`. The detached WSL shell runs the
  sealed shard driver, verifies 108 manifests, then automatically runs 36
  evaluation shards, aggregate, and manifest. It is not a child of the Codex
  unified execution session. A nonzero phase stops the pipeline.
- No retry in R472. Any post-seal scientific or orchestration failure requires
  another successor; imported R471 artifacts remain immutable.

## Formal launch contract

- `formal_entry`: `scripts/run_r472_u2_source_factorial.py <phase>`
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r472_u2_source_factorial.py rehearse`
- `rehearsal_scope`: `sac_semantics_probe`, objective/reward identities,
  donor/reuse audit, hardlink identity probe in scratch, terminal truth table,
  initialization parity, and real three-step ANDES update; no formal root.
- `capacity_evidence`: `memory/rounds/R472/capacity_evidence.json`
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
- No outcome authorizes a universal intrinsic communication claim.

## 资产保护契约

Preserve R431/R438/R451/R460/R470/R471 and imported GPT material byte-for-byte.
Add only the R472 adapter/test, pre-attempt audit, hardlink-based result root,
missing training/evaluation results, analysis/report/claim/verdict, and final
package. Do not inspect R471 endpoint outcomes before R472 aggregation; only
validity, steps, identities, and hashes may gate reuse.

## Cross-references

- R471: 16 validity-complete shards plus an external-session interruption; no scientific conclusion.
- CLM-1315: endpoint and paired-seed definitions.
- CLM-1360: same-learner 16-worker capacity.
- CLM-1440: executed-action Bellman semantics.

## Theory intake

- Retained: source intervention, donor marginal identity, paired log effects,
  Holm control, and physical executed-action semantics.
- Prediction: `N` improves held-out primary loss over marginal-matched `P` by
  more than 10% for at least one role without a half/final direction flip.
- Blocked: intrinsic/topology-general communication value and any partial R471
  endpoint interpretation.
