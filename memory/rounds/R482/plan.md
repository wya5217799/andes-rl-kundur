---
round: R482
state: active
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-25'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R482 plan — corrected-card learning re-verification + all-fresh source factorial (final high-cost experiment)

**Opened**: 2026-08-25
**Driver**: owner launch decision OWNER-APPROVED 2026-08-25 (learning_reverification_launch_decision_20260825.md): run corrected-plan Phase 3 (minimal learning ladder) + Phase 4 (all-fresh source factorial) as one round, local host, frozen 26-seed design, experiment-termination clause, owner code-review gate before any execution. The R481 deterministic bank closed DIRECT-MD-FORMAL-PASS (CLM-1505), which satisfied prospective decision condition 7 and opened training.
**Parent**: R481 completed (CLM-1505); R477 (CLM-1480) is the n=6 design predecessor whose cells are never reused; corrected plan 20260824 Phases 1A/2 gates passed (R478/R481).

## TL;DR

Train 234 all-fresh cells under the corrected card: 26 Phase-3B RMS-penalty cells (waves 1-2) + 208 factorial cells (8 arms x 26 fresh seeds 501..526, waves 3-15), 43,200 interaction steps per cell (unchanged), 16 workers + launcher, then 18 arm-stage evaluation jobs. Analysis = the frozen four-hypothesis materiality design (exact one-sided Wilcoxon at the log(1.10) boundary, Holm 4, FWER 0.05) via the frozen power plan + a newly registered Phase-3 trade-off pair. Zero carryover; fresh base states per seed matched across all nine arm slots. Measured wave wall ≈ 3.0 h (R477) -> ETA ≈ 44-52 h. Outcomes: MATERIAL-MAIN-EFFECT / MATERIAL-INTERACTION / MATERIAL-EFFECT-NOT-ESTABLISHED / PHASE3-TRADE-OFF-REPRODUCED / PHASE3-TRADE-OFF-NOT-ESTABLISHED / DESIGN-INVALID / EXECUTION-INCOMPLETE / INTEGRITY-INVALID.

## Snapshot at plan-time (oracle as of 2026-08-25)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] finite-bank information-level margin program — not addressed by this round.
- External review (2026-08-25, owner-pasted): interaction structure beyond the two registered interactions (actor x reward, three-way) is out of scope here; recorded as a future-program pointer, not a round question.

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375.
- Q-0004 closed-negative @ R442, by CLM-1370.
- Q-0111 closed-negative @ R397, by CLM-1130.

## Development diagnostic wave (owner-approved 2026-08-25)

- Purpose: engineering-health + training-dynamics smoke test on the corrected card before the formal waves; the owner reviews the diagnostic report with FULL visibility. Development cells are burned forever and never enter formal inference.
- Roster (frozen in the seal shard_lists): 16 cells = 8 x an_cn_r1 (dev seeds 601-608) + 8 x an_cn_r1_rms (dev seeds 609-616); one wave, 16 workers; expected wall ≈ 3 h (R477 measured 10,803 s per 16-cell wave).
- Outputs: results/research_loop/r482_u2_confirmatory/dev/ (create-only, hashed sidecars); excluded from missing_shards, formal manifests, and every formal analysis.
- Gate: the detached pipeline pauses after the development wave until tmp/andes/r482_formal_go.json exists (owner continuation authorization). Decision paths: (a) continue the formal waves with the UNCHANGED frozen design; (b) any scientific-parameter/budget/roster change -> successor round with new registration + new seal (no in-place tuning); (c) stop -> close with EXECUTION-INCOMPLETE, dev artifacts preserved.
- Blindness rule: formal scientific outcomes stay blind until the formal batch completes; the dev wave is visible by design.

## Frozen scientific contract

- Card: corrected project calibration, device-base H0=100 s (M0=200 s), D0=100, one-convention conversion exactly once (R478 repair6). V4 regression green; zero-action preserves runtime M/D.
- Learner/bank/projector: frozen R470-family contract (source_factorial_sac + executed_action_sac byte-identical; no retune). Budget 43,200 interaction steps per cell, unchanged. Checkpoints half + final; final primary.
- Factorial arms: an_cn, an_cp, ap_cn, ap_cp x r0,r1 (actor {N,P} x critic {N,P} x reward access {0,1}); seeds 501..526 (fresh; power-plan roster). P = same-time row permutation rho(i)=(i+1) mod 4 of the authentic N neighbour 4-tuples (guardrails A.1/A.2; no exogenous donor bank).
- Phase-3B arm `an_cn_r1_rms`: authentic-source cell (actor N, critic N, reward access 1) with the R433-frozen action-stress penalty grafted onto the UNCHANGED factorial base reward: r_i' = legacy.step_rewards(...) + lambda_p * p_i, p_i = -mean_j(a_ij^2) over the projected executed action, lambda_p = 10.0 frozen (R433 dev-lambda selection); no coefficient re-selection after result visibility; single change = penalty term (R424 target-semantics gate: rehearsal runs the penalty-semantics probe; penalty lowers reward).
- Base states: 26 fresh base states (one per seed), generated on the corrected card pre-training, RNG seed = 200,000 + seed, rng set before environment, create-only manifests + sha256, matched across all nine arm slots per seed. Old seeds 401..406 base states never reused.
- Profiles: canary_eval_a..d (frozen power-plan roster); scenario definitions = the sealed R476/R477 evaluation profile definitions (bound by hash in the seal source map); fixed evaluation scenarios of the frozen design, not model-selection holdouts — fresh inference units are the seeds.
- Analysis: four registered hypotheses (actor_main, critic_main, actor_x_critic, critic_x_reward); materiality boundary log(1.10); exact one-sided Wilcoxon signed-rank at the boundary; Holm over the four materiality p-values; FWER 0.05; ties/zeros invalidate (no asymptotic fallback); bootstrap/leave-one-out descriptive only. actor x reward and the three-way interaction: registered OUT OF SCOPE.
- Symmetry check (registered): Fisher-Pearson moment skewness g1 of the boundary-centred seed effects; if |g1| > 1.0 the primary test switches to 1,000,000 fixed-seed sign-flip permutations (one-sided, p reported with its Monte Carlo SE); otherwise the exact Wilcoxon remains primary. Both reported. The sign-flip test is also the registered primary when the exact Wilcoxon is invalid (zero differences or tied absolute ranks) — no asymptotic fallback exists.
- Power plan: source_factorial_power_plan.json (n_star=26; power 0.9868/0.9868/0.9694/0.8189, Wilson lower 0.8172) — hash-bound in the seal. R476/R477 power_analysis files are the legacy n=6 design; never cited as the n=26 authority. The embedded planner sha256 is stale (planner changed at a5bd163): the artifact is regenerated from unchanged design inputs and must reproduce n_star=26 and all four power values before seal (guardrails G.6 create-only refresh).
- Wording: total algorithm effect of authentic-neighbour vs row-permuted-placebo source; never pure semantic value, zero effect, or equivalence.

## Experiment termination clause (owner-mandated)

After R482 closes, the corrected-plan experiment program is exhausted: Phase 1/2 closed (R478/R481), Phase 3/4 = this round, Phase 3D / the energy-port residual learner is formally EXCLUDED (energy-port claim terminal, CLM-1490). Remaining work = manuscript lane only (replace numbers/figures/claims, coordinate-sensitivity offline report, parameter-card rationale, venue audits). Any new experiment requires a fresh owner decision + a new round. Registered in LINE.md objective and stop_when.

## Owner gates (owner-mandated)

1. Code review before ANY execution: after implementation, NO WSL/ANDES invocation — not rehearsal, not base-state generation, not training — before the owner reviews the code and plan.
2. Notify the owner at each launch moment (base-state generation, rehearsal, capacity confirm, each training launch).
3. Pre-seal owner approval record (OWNER_APPROVED.json) required before execute.

## Design-completeness gate (before seal; all six statistical-audit fixes)

1. Phase-3 inference registered (Pre-registered outcomes below).
2. Power artifact hash-bound (seal power_sha256); legacy n=6 files marked.
3. Wilcoxon symmetry check + sign-flip fallback registered (above).
4. Profile definitions + metric formula frozen by hash (seal source map; metric disturbance_differential_energy per source_factorial_design.py PRIMARY_METRIC; power-plan source csv bound).
5. Phase-3B reward level (r=1) + base-state reuse (26 shared fresh base states) pinned; ordering: 3B cells first (waves 1-2), then factorial (waves 3-15), ONE batch, Phase-3 verdict after batch completes; 3A (projected-SAC reference) = the batch's an_cn_r1 arm, consumed once — no duplicate training.
6. actor x reward and three-way interactions out-of-scope (registered).

## External review intake (guardrails G.5)

- gpt_pro_md_base_conversion_impact_answer_20260825 (owner-provided; staged in-repo at paper/yang_md_decoupling_marl/working/, byte-hash-verified against its 05_文件校验.md): read + assessed 2026-08-25. P0: none. P1: offline recomputation list (high-resolution first-interval trajectories, corrected-equilibrium DAE matrices, coordinate-sensitivity) -> assigned to analysis/manuscript lane, not blocking launch. Forbidden-statement list (15 items) -> binds feed/claim wording at close-out.
- Owner-pasted paper review (2026-08-25): four structural concerns + story framing. Dispositions: carryover blemish -> solved by the all-fresh design; interaction concern -> two registered interaction tests; coordinate physics -> offline sensitivity reports + wording discipline (registered coordinate wording only); M/D parameter rationality -> parameter-card rationale surfaced in manuscript + CLM-1500 H-sensitivity cited; story framing ("action interface over MARL information") -> manuscript rewrite. NOTE: the review's energy-port success citation is OUTDATED (corrected-object failure; claim terminal) and must not be cited as supporting evidence.

## Pre-registered outcomes (expected vs actual)

- Factorial: DESIGN-INVALID / EXECUTION-INCOMPLETE / INTEGRITY-INVALID -> no effect verdict (material_effect=NOT_TESTED). MATERIAL-MAIN-EFFECT: at least one main-effect materiality null rejected. MATERIAL-INTERACTION: at least one interaction materiality null rejected. MATERIAL-MAIN-EFFECT+MATERIAL-INTERACTION: both hold simultaneously (combined verdict registered here). MATERIAL-EFFECT-NOT-ESTABLISHED: validity complete, no registered rejection (never written as zero effect or equivalence). No outcome-based early stop.
- Phase 3: PHASE3-TRADE-OFF-REPRODUCED: both one-sided paired tests reject in the frozen directions under Holm (family of 2, FWER 0.05) — (a) endpoint regression: per-seed paired log[L(RMS)/L(SAC)] > 0 on final checkpoints, exact one-sided Wilcoxon at zero; (b) action-stress improvement: the R433-frozen action-RMS row metric decreases. PHASE3-TRADE-OFF-NOT-ESTABLISHED: validity complete, one or both not rejected. Same invalid classes as the factorial. Guard rows reported descriptively (R431/R433 row style).
- Phase-3 dual metric (CLM-0430): the geo pair above is primary; the feed and verdict MUST also report the paper cum_rf counterpart (compute_global_cum_rf over the same sealed eval records, per-seed paired sac-minus-rms diffs, direction registered: penalty regresses cum_rf, one-sided p at zero as a report line). If cum_rf rejects while geo does not (or vice versa), the verdict reports both directions explicitly; follow-up threshold for a future round = cum_rf one-sided p < 0.05 in the registered direction.

## Theory intake

- External redesign prediction (inherited R476/R475): the clean row-permuted placebo either establishes an actor or critic effect above 10% under the direct Holm, or the effect is not established at that bar.
- Phase-3 prediction (old descriptive direction, frozen): the RMS penalty removes action-stress failures at the cost of endpoint regression.
- External audit prediction: no common-plant cancellation — fresh cells required (design enforces).
- Observables: per-seed paired log effects, Holm rows, half/final direction, curve stability, routing mutation flags, symmetry diagnostics, Phase-3 paired rows, every integrity field.

## Methodology

1. Implementation (this round): fresh base-state generator (corrected card, 26 seeds), runner scripts/run_r482_u2_confirmatory.py (adapts the sealed R477 machinery: seeds 501..526, nine arms, zero import/carryover, four-test aggregation wired to source_factorial_design.py, Phase-3 pair), detached pipeline scripts/run_r482_detached_pipeline.sh (15 waves, ETA recalibration after wave 1, eval phase), tests tests/test_run_r482_u2_confirmatory.py, power-artifact regeneration test fix (stale planner sha256).
2. Freeze order: code -> power-artifact regeneration (design unchanged, verify n_star=26) -> dual review (one adversarial reviewer per guardrails G.2; reviewer scratch only under tmp/) -> preflight -> OWNER CODE REVIEW GATE -> base-state generation (WSL, create-only) -> rehearsal via the SAME pre-attempt path (source/parent hash, installed package/case, output absence, R424 gradient probe) -> capacity (16x8 quick confirm + evidence JSON) -> seal -> commit -> owner approval -> execute.
3. Execute: detached pipeline launched as a background job via `wsl -d Ubuntu bash /mnt/e/Projects/andes-rl-kundur/scripts/run_r482_detached_pipeline.sh` (handoff workaround for launch_detached.py backslash mangling); 16 workers + launcher; no polling, completion notice wakes the session.
4. Aggregate: four-test boundary analysis + Phase-3 pair + symmetry diagnostics; classify; verify all hashes.
5. Close-out: claim -> feed -> publication gate -> verdict -> MANIFEST -> LINE evidence_refs -> close.

## Experiment efficiency card

- execution_class: non-quick
- job_count: 252 unique jobs = 234 fresh training cells (26 Phase-3B + 208 factorial) + 18 arm-stage evaluation jobs (2 Phase-3B + 16 factorial)
- concurrent_jobs: 16; one launcher; one native numerical thread per process
- waves: 1 development wave (16 cells) + 15 formal training waves + 1 evaluation phase (18 shards)
- eta_range: 44-52 hours wall after launch
- eta_basis: R477 wave-1 measured 10,803.253 s for 16 cells (eta_recalibration.json); R476 card 8-12 h for 3+1 waves (consistent); R475 52-minute live no-failure training canary
- eta_recalibration: after wave 1 (16 Phase-3B cells), recompute remaining range from observed wall; scope and concurrency unchanged
- artifact_budget: expected ≈ 2.5 GiB; hard stop for review above 3.2 GiB before manifest finalization
- completion_rule: 234 valid 43,200-step training manifests, all 18 evaluation jobs complete (9 arms x half/final covering 26 seeds), aggregate and formal manifest hash-valid
- stop_rule: any seal/review/routing/rehearsal/hash/shard failure, nonfinite learner output, failed TDS, missing sidecar, or budget overrun stops the pipeline
- retry_rule: none inside R482; a scientific or integrity failure requires a successor
- interruption_rule: operator shutdown may terminate processes; mid-shard files are incomplete and never scientific
- interruption_artifacts: completed hash-valid shards + logs preserved and inventoried; partial shards excluded
- resume_policy: no same-round resume; a successor prospectively declares any completed-shard reuse

## Formal launch contract (skeleton; filled at seal)

- formal_entry: /home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r482_u2_confirmatory.py <phase>
- rehearsal_command: same entry rehearse; rehearsal_scope: same-pre-attempt-path; rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R482/capacity_evidence.json (R452-R477 16-worker ladder precedent; R477 two measured training waves; R475 52-min live canary; R481 corrected-family 16-worker bank; one 16x8 quick confirm on the corrected family)
- wsl_python_processes: 17 (16 workers + 1 launcher)
- native_threads_per_process: 1
- host_process_budget: 17
- other_reserved_processes: 0 (re-verified at launch: no active rounds, no duplicate WSL jobs)

## Gate

- ENGINEERING failures classify DESIGN-INVALID / EXECUTION-INCOMPLETE / INTEGRITY-INVALID as registered; no retry, partial artifacts preserved, any post-seal change requires a successor round + new seal.
- The 3B-first wave order is fixed; the factorial has no outcome-based early stop; Phase-3 verdict is computed after the batch completes.

## 资产保护契约

R470-R481 chains, the sealed R476/R477 runner machinery, the frozen power plan design inputs, R433 reward contract, and all historical evidence stay byte-identical. The power-plan artifact is refreshed mechanically only (regenerated from unchanged design inputs; design content must reproduce). Add only: this round's plan/verdict/contract/seal/capacity/rehearsal/base-audit artifacts, fresh base-state files + sidecars, one successor runner + pipeline + tests, and results/research_loop/r482_u2_confirmatory/. Old cells, old base states, and viewed holdouts are never reused, pooled, or edited.

## Manuscript handoff (post-close; manuscript lane, no new experiments)

- Coordinate-sensitivity offline report on corrected trajectories: inertia-weighted COI common coordinate vs registered arithmetic coordinate; nominal-modal projection subspace angles; endpoint rankings and guard flips.
- M/D parameter-card rationale surfaced (md_parameter_card_justification_20260824.md) + CLM-1500 H-sensitivity cited as measured parameter-sensitivity evidence.
- Story reframing per external review: action-interface main line; energy-port success NOT cited (terminal); forbidden-statement list bound; "registered coordinates" wording only.

## Open items for owner review (before seal; recommended defaults registered)

- O1: Phase-3 registered inference = the two one-sided Holm pair above (recommended).
- O2: base-state generation spec = RNG 200,000 + seed, corrected card, 26 fresh states (recommended).
- O3: wave order = Phase-3B cells first (waves 1-2), then factorial (recommended).
- O4: termination-clause wording in LINE.md/plan as written (recommended).
- O5: Phase-3D exclusion registration as written (recommended).

## Cross-references

- paper/yang_md_decoupling_marl/working/learning_reverification_launch_decision_20260825.md
- paper/yang_md_decoupling_marl/working/corrected_md_revalidation_experiment_plan_20260824.md
- paper/yang_md_decoupling_marl/working/prospective_direct_md_successor_decision_20260825.md
- paper/yang_md_decoupling_marl/working/source_factorial_power_plan.json
- paper/yang_md_decoupling_marl/working/md_parameter_card_20260824.json + justification
- scripts/run_r477_u2_confirmatory.py, scripts/run_r476_u2_confirmatory.py, scripts/soft_spot_shard_driver.py
- src/andes_rl_kundur/evaluation/source_factorial_design.py, u2_confirmatory.py
- memory/rounds/R476/plan.md, memory/rounds/R477/, memory/rounds/R481/plan.md
- paper/yang_md_decoupling_marl/working/gpt_pro_md_base_conversion_impact_answer_20260825 (external audit, staged + hash-verified + registered)
