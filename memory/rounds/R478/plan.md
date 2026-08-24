---
round: R478
state: active
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-24'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R478 plan — corrected M/D base-convention revalidation: Phase 0 build + Phase 1 banks, owner review gate before formal execution

**Opened**: 2026-08-24
**Driver**: Corrected-M/D revalidation program, Phase 0 + Phase 1. `GENCLS.M/D` are base-converted power parameters; the V4 reset path records the unconverted M baseline as the interpolation anchor, so a zero first action can change runtime inertia while the reported action increment is zero. One device/system-base convention is enforced, invariants proven, deterministic banks rebuilt under the corrected card; no formal attempt before the owner reviews the frozen program.
**Parent**: corrected_md_revalidation_experiment_plan_20260824.md (authority); ADR-0019.

## TL;DR

R478 freezes a project-calibration parameter card with an explicit non-Yang provenance boundary, implements the single conversion fix in the shared reset/anchor path, and proves the offline 0C invariants. The owner's 2026-08-24 continuation authorizes only the zero-family capacity measurement and serial semantic rehearsal; it does not authorize a formal attempt, deterministic bank, training, or factorial. A passing invariant opens one deterministic canary, not the whole bank. Branch-specific formal revalidation follows only when the lower gate survives. The 224-job factorial is a deferred shelf plan and is never the next execution queue. Formal work still requires final-source capacity/rehearsal/seal and owner approval bound to every seal hash.

## Pre-seal corrective amendment (2026-08-24)

- The code/design repair is authorized. The owner's later instruction authorizes only zero-family `measure-capacity` and `rehearse`; training and formal execution remain forbidden.
- Capacity/rehearsal artifacts produced before the invariant gate and final review are quarantined. They are old-generation, non-authoritative, excluded from every future seal, and remain preserved byte-for-byte.
- The current repaired authority namespace is `repair3`; its artifact and shard paths cannot collide with quarantined files. The earlier `repair1` capacity run is quarantine-only because source/runtime identity was not bound across the full ladder and the runner changed before interpretation. The unused `repair2` authorization is also quarantine-only because its registered plan path was inconsistent before launch.
- Missing corrected regression fixtures fail closed. They may only be generated after the final source freeze and explicit physical-execution authorization.
- Conclusion dependency is terminal: semantic invariant failure stops every corrected-object claim; a deterministic-canary flip opens only the affected deterministic bank; training and the factorial remain closed until all upstream conclusions survive.
- Parallelism is inside the current gate only: unique capacity/canary jobs may run concurrently at the measured safe worker count, but downstream gates never run speculatively in parallel.
- Every completed semantic/canary/formal gate receives a create-only report recording frozen input and output hashes, validity, registered metrics, comparison with the corresponding old Yang-line conclusion, the decision `retain old route` or `redesign successor`, and exactly one next gate.

## Frozen scientific contract

- One scientific change: M/D initialization, runtime application, telemetry, and interpolation anchors use one declared device/system-base convention; conversion happens exactly once. Everything else (laws, gains, profiles, split, window, endpoint definitions, guards, topology list, exclusion gates) unchanged.
- Parameter card fields: `S_n,i`; `S_b`; device-base `H_i`, `M_i=2H_i`, `D_i`; runtime system-base M/D; normalized-to-physical action map; clamps + slew rule; units + conversion equation per field.
- The card is inherited project calibration held fixed to isolate the conversion correction, never selected from controller performance. Yang2023 does not supply enough baseline/unit information for a strict benchmark card; Phase-1 claims remain project-calibration finite-bank claims.
- Old artifacts preserved as historical evidence, byte-for-byte; the corrected bank has distinct identity and result root; old and corrected numbers are never pooled.
- Deterministic banks: selection uses development profiles once; evaluation profiles remain unseen; no retune after evaluation visibility.

## Engineering correction contract

1. Fix lands in the shared reset/anchor path (`base_env.py` / `andes_vsg_env_v4.py`; NOTES_ANDES.md read before edits). Anchor = declared system-base runtime value; reported action increments use the same convention; telemetry readback compared in that convention. Reviewer-C extensions: V5's two heterogeneous-D build writes converted once (`andes_vsg_env_v5.py`), and the distributed-residual wrapper converts the runtime readback to device-base model units at its boundary (`distributed_residual_env.py`).
2. V4 regression expectations are fail-closed until corrected baselines are generated after the final source freeze; documented as the single deliberate change; historical checkpoints stay historical and are never imported into the corrected bank.
3. Card + conversion helpers = reusable implementation in `src/andes_rl_kundur/`; invariant tests in `tests/`; bank adapters as stable scripts; governance shell (seal verification, fail-closed classification, dual review of one identical final source map, mutation tests) reused from the R477 pattern.
4. Comparison identifiability: corrected vs historical numbers are compared only in the manuscript/review layer; within-bank comparisons are corrected-only.

## Methodology

1. 0A/0B: audit primary sources; write + register the parameter card and justification note in ARTIFACTS.
2. 0C: write the seven invariant tests red-first (zero action; telemetry; round trip; heterogeneous card; nonzero-action branch/clamp/slew units; energy-port slow channel; reset repeatability). Confirm the zero-action invariant fails pre-fix (bug reproduced).
3. Implement the conversion fix; all invariants green; V4 regression re-locked green.
4. Locate the registered frozen banks (zero-action, nine-law, dev/eval schedule, energy-port unseen/extra-condition, topology variants) and re-point them at the corrected card via `scripts/run_r478_md_revalidation.py`: parent sealed runners stay byte-identical (line-ending-independent frozen source hashes), the adapter patches authority paths into the `repair3` namespace and records a source-keyed sidecar. The reusable probe module, not the runner, owns zero-action scenario selection, physical execution, and validity checks. Guards/profiles/split/windows remain unchanged.
5. Freeze-then-review: two independent reviews of the frozen commit + file hashes; P0/P1 repaired before seal.
6. Freeze and dual-review the final source map. Record the owner's bounded physical authorization in a hashed `physical_execution_authorization_repair3.json` bound to the exact runner/plan/card and approved family commands.
7. Under the current bounded authorization, run only the zero-family final-source capacity ladder (1/2/4/8/12/16 workers, exactly 32 representative jobs per rung, borderline 3%-7% gain remeasured once), then the serial semantic rehearsal through the same pre-attempt path. No corrected deterministic bank or baseline is opened by this authorization.
8. STOP — owner formal gate. Every execution command verifies a hashed owner-approval artifact whose per-family entry equals the current seal hash. No formal attempt, retry, or result inspection exists before that check passes.

## Codex review intake (2026-08-24)

Frozen range reviewed by Codex: NOT-APPROVED; every finding below is addressed in this round:

- P0 formal-execution seal/owner gate: code-enforced via `_require_launch_authority` (seal command + OWNER_APPROVED marker) blocking all physical commands.
- P1 frozen R453 runner mutated: reverted to byte-identical; the v4-env drift contract now lives in the R453 test layer (exact-drift pin + strict xfail for the blocked inventory test).
- P1 regression baseline missing -> silent skip: corrected baselines committed as test fixtures under `tests/fixtures/eval_v4_baseline_R478/`; missing fixture now FAILS the gate.
- P1 failure-step telemetry untruthful: `base_env.step` now reads back the actual runtime M/D after the substep loop; `_prev_M/_prev_D` and `M_es/D_es` telemetry derive from readback (unchanged on success paths).
- P1 scope pollution in the first R478 commit: the manuscript/supplement/figure files swept by the governance-clearing commit are registered verbatim from the prior planning session; documented here, never part of the scientific change; future commits carry only R478-owned paths.
- P1 adapter exceeded thin-adapter duty: zero-family scientific logic moved to `src/andes_rl_kundur/evaluation/r478_zero_action.py`; the runner only dispatches.
- P2 CRLF hashing: parent-source hashes are now LF-normalized (CRLF checkouts verify identically).
- P2 test gaps: V5 full-regca1 branch test added (non-strict xfail, documented as practically unusable until post-approval verification); substep-level slew observation left to the bank record loops (declared).
- Accepted, no code change: pre-ruling capacity/rehearsal artifacts stay as development evidence (non-claim-bearing, pre-approval); no further ANDES execution before owner approval.

The later `repair3` amendment above supersedes the original global seal/approval
mechanism described in this review intake: authority is now command-scoped and
bound to the exact per-family seal hash.

## Gate

- INVARIANT-GATE: all seven 0C invariants green before any simulator bank; any failure = engineering invalidity, no scientific run follows.
- GATE-1A: development profiles select exactly one schedule using the frozen priority/tie rule. Only that winner reaches evaluation. It must be finite and guard-valid on all four registered evaluation profiles; one-to-three passing profiles cannot open the gate. Failure stops direct-M/D learner training, with no evaluation-visible fallback.
- GATE-1B: frozen energy-port controller passes its registered contract; else drop/redesign the constructive companion in a new plan; no tuning in this run.
- GATE-1C: complete frequency/M-D/action/topology/disturbance traces retained for every valid record.
- Integrity: paper-facing EIG passes TDS.test_ok + exit_code=0 + init residuals + finite spectrum + positive-real guard (CLM-0665).
- Claim hygiene: any paper-reward-ablation headline must cite geo + cum_rf (dual_metric_lint at claim time).

## Theory intake

No external mathematical theory this round; the base convention is primary-source engineering. external_theory_intake_lint N/A.

## Experiment efficiency card

- execution_class: non-quick
- job_count: deterministic Phase-1 total remains symbolic until the repaired inventories are frozen; the later source factorial is prospectively frozen at 224 unique jobs (208 training + 16 evaluation)
- concurrent_jobs: unresolved until the mandated 1/2/4/8/12/16-worker, 32-jobs-per-rung final-source ladder is authorized and measured
- waves: unresolved until job count and measured concurrency are both frozen
- eta_range: unset until corrected rehearsal/first-wave timing exists (do not invent)
- artifact_budget: symbolic; hard review stop set at seal from rehearsal disk telemetry
- completion_rule: every registered bank job valid + trace bank complete + manifest hash-valid
- stop_rule: any invariant/seal/review/routing/rehearsal/hash failure, nonfinite output, failed TDS, or missing sidecar stops the pipeline; no in-round patch or retry
- retry_rule: no silent retry; failed attempts preserved; post-seal source or contract change requires a successor round
- interruption_rule: operator shutdown may terminate processes; partial artifacts are never scientific; resume requires a successor that prospectively declares reuse
- owner_review_gate: after seal+rehearsal, formal attempts are BLOCKED until the owner approves the frozen program (pre-registered, not a gate-lifecycle change)

## Formal launch contract

- formal_entry: scripts/run_r478_md_revalidation.py <family> <phase> (families: zero|ninelaw|schedule|port_unseen|port_extra_k35|port_extra_k4|topology; parent runners stay byte-identical, rekey sidecar per dispatch)
- zero_preformal_order: contract -> measure-capacity -> rehearse -> prepare(seal)
- port_unseen_preformal_order: measure-capacity -> rehearse -> prepare(seal)
- rehearsal_command: /home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r478_md_revalidation.py <family> rehearse
- rehearsal_scope: same-pre-attempt-path
- rehearsal_checks: source_hash,parent_hash,installed_package,installed_case,output_absence
- authority_generation: repair3
- physical_execution_authorization: `memory/rounds/R478/physical_execution_authorization_repair3.json`, create-only hashed artifact bound to exact runner/plan/card; current allowlist is only zero-family `measure-capacity` and `rehearse`
- capacity_evidence: per-family `memory/rounds/R478/capacity_*_repair3.json` artifacts, produced only after explicit physical authorization and bound to matching pre/post source and runtime snapshots
- seal_source_scope: all repository Python modules dynamically loaded by the physical rehearsal plus runner/plan/card/parent; seal also binds installed ANDES module/distribution and Kundur case hashes
- formal_owner_approval: `memory/rounds/R478/formal_owner_approval.json`, create-only and hash-bound to each approved family seal
- wsl_python_processes: 1 (port_extra_k35/port_extra_k4 frozen-parent serial seam) / 17 (port_unseen 16 parallel, measured repair5 ladder)
- native_threads_per_process: 1
- host_process_budget: 1 (port_extra_k35/port_extra_k4 frozen-parent serial seam) / 17 (port_unseen 16 parallel, measured repair5 ladder)
- other_reserved_processes: 0

## 资产保护契约

Preserve R398-R477 artifacts, all imported external-review material, every historical checkpoint, the premature R478 capacity/rehearsal files, and all `repair1`/`repair2` files byte-for-byte. These files are quarantine-only and never enter `repair3` authority. Add only: parameter card + justification, conversion fix + invariant tests, corrected bank adapters + trace capture, reviews, `repair3` seal/rehearsal artifacts, corrected result root (distinct identity), feed/claim/verdict. Historical results are never pooled with corrected results.

## Cross-references

- paper/yang_md_decoupling_marl/working/corrected_md_revalidation_experiment_plan_20260824.md (authority)
- paper/yang_md_decoupling_marl/working/source_factorial_power_plan.json (prospective statistical contract; no new training outcomes)
- docs/adr/0019-separate-yang-md-decoupling-marl-successor.md
- docs/eng-notes/NOTES_ANDES.md (required before env edits)
- CLM-0665 topology/EIG hard gate; R477 structure template (plan, efficiency card, launch contract)

## Post-run quarantine audit (2026-08-25)

- The bounded `repair3` authorization covered only zero-family capacity and
  rehearsal. Those two artifacts remain the only authority-valid physical
  outputs of this generation.
- The direct-M/D and energy-port confirmation runs launched afterward were
  not listed in the repair3 allowlist. Preserve their raw files and reports,
  but classify them only as development-visible diagnostics. They cannot
  enter a formal seal, claim sheet, manuscript number, or route verdict.
- Viewing `eval_a` through `eval_d` consumed their holdout status. They are
  never reused as unseen evaluation evidence. Any successor formal bank must
  prospectively register genuinely fresh profile identities before execution.
- The frozen canary route remains authoritative: the next official gate is
  still the deterministic energy-port bank unless the owner approves a
  successor decision that abandons the energy-port claim. No direct formal
  bank is open.
- `repair3` is closed to further physical commands. A future attempt requires
  a new authority generation, an exact plan allowlist for every probe/profile,
  fail-closed WSL/scratch entrypoints, and matching pre/post transitive source,
  installed ANDES, and Kundur case identities.

## Repair4 authority generation (2026-08-25)

- Owner start instruction (2026-08-25): re-seal on the merged final sources,
  then run the energy-port family capacity ladders and rehearsals before any
  formal execution decision.
- `AUTHORITY_GENERATION` moved `repair3` -> `repair4` in the adapter; the
  `repair3` authorization and all `repair1/2/3` artifacts stay byte-for-byte
  quarantine. No `repair3` command can run under `repair4`.
- `repair4` allowlist (owner-approved): `port_unseen`, `port_extra_k35`,
  `port_extra_k4` -> `measure-capacity`, `rehearse`. No formal bank, no
  `prepare`/`execute`/`classify`, no direct-M/D, no ninelaw/schedule/topology
  physical command under this generation.
- After ladder + rehearsal, STOP: report measured budgets and rehearsal
  evidence to the owner; formal execution requires a per-family
  `formal_owner_approval.json` bound to each `repair4` seal hash.
- Owner scheduling directive (2026-08-25): time is pressing — use the
  hardware as fully as possible and parallelize as much as possible.
  Interpretation within the frozen contract: pick the highest safe worker
  rung inside the measured memory budget; formal families run at the maximum
  measured concurrency (distinct output roots, no cross-family evidence
  pooling); per-family ladder/rehearse stay serial only where the contract
  requires it (no speculative downstream gates).

## Repair5 fast-ladder amendment (2026-08-25)

- Process error recorded: the `repair4` ladder was launched after a second
  plan.md edit (owner scheduling directive), so the authorization source
  binding drifted and the port_unseen ladder results were not persisted.
  Lesson: generate the authorization artifact only after every plan/source
  edit is committed.
- Owner directive (2026-08-25): do not re-run the full six-rung ladder; the
  same host and ANDES deterministic workload already measured it repeatedly
  (R452-R477 all selected 16 workers; R458 schedule ladder on 2026-08-24;
  R478 zero repair3 on corrected code). Full 1/2/4/8/12/16 x 32 ladders are
  over-insurance for this round.
- `repair5` reduces the ladder to one 16-worker rung of 8 jobs per family:
  a re-confirmation of 16-way parallel safety (RSS/throughput) on the
  corrected sources only. `AUTHORITY_GENERATION` moved `repair4` -> `repair5`;
  `repair4` files stay byte-for-byte.
- `repair5` allowlist (owner-approved): `port_unseen`, `port_extra_k35`,
  `port_extra_k4` -> `measure-capacity`, `rehearse`. Same stop point: report
  ladder + rehearsal evidence to the owner; formal execution requires a
  per-family `formal_owner_approval.json` bound to each `repair5` seal hash.

## Snapshot at plan-time (oracle as of 2026-08-24)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program (shared action variables per non-anticipative info class, solution section 5.4) certify or refute INFORMATION-LIMITED for the 2% joint target under the exact R352/R353 observation histories?

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?
