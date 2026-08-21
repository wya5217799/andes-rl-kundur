---
round: R429
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-18'
closed: '2026-08-18'
supersedes_rounds: []
superseded_by_round: null
abort_reason: sealed inherited-runner default bound SAC output to R428; six SAC shards
  were create-only rejected before R429 training, three scalar shards were interrupted,
  engineering_failure.json preserved; owner explicitly authorized a higher-parallelism
  successor
superseded_note: null
---
# R429 plan — topology-adapted SAC on the frozen matched bundle

**Opened**: 2026-08-18
**Driver**: owner direct order in the current task: close the missing matched-bundle
comparison for the repository's topology-adapted SAC and use as much safe host
parallelism as measured capacity permits.
**Parents**: CLM-0045, CLM-0048, CLM-0059 are historical design inputs only;
R428/CLM-1305 is the matched exact-paper-interface endpoint; R425/CLM-1290 is
the matched CD-family endpoint. Historical checkpoints, values, and claims are
not evidence for R429.

## TL;DR

Workload: `evidence`; frozen training + evaluation. Keep the R428 matched
bundle, profiles, seeds 401/402/403, 43,200 interaction steps per run,
deterministic evaluation, estimators, classifier, guards, scalar anchor, and
direct M/D action object. Replace only the two R428 exact-paper SAC slots with
the repository's byte-unchanged `SACAgent` package and the historically
implemented normalized-action-cost reward. This is a targeted endpoint
comparison, not tuning or an algorithm sweep.

## Frozen scientific contract

Three learning arms retain the matched-contract identifiers so the frozen
classifier remains byte-reused:

- `yang_scalar_td3`: R419/R425 scalar anchor, same learner/reward/projector and
  checkpoint byte-anchor rule.
- `cd_matd3_no_message`: four independent topology-adapted SAC agents; actor
  inputs keep slots 0:3 and honest-zero slots 3:7.
- `cd_matd3_message`: the same four SAC agents with the full seven-slot local
  and neighbour observation rows.

The two SAC identifiers are compatibility slots; R429 records an explicit
`arm_algorithm_map` so they are never described as CD-MATD3.

Learner bundle, read from the byte-unchanged historical implementation:

- per agent: Gaussian+tanh actor, independent twin-Q critic and twin-Q target,
  automatic alpha, target entropy -2;
- four hidden layers of width 128; lr 3e-4; gamma 0.99; tau 0.005; replay
  capacity 10,000; batch 256; alpha bounds [0.005, 5.0]; gradient-norm cap 1.0;
- one learner update per environment step after replay reaches batch size, as
  in the R428 matched interaction/update schedule; no warm start, checkpoint
  reuse, tuning, or outcome-based selection;
- stochastic policy during training; deterministic actor mean at evaluation;
  raw tanh action goes directly to the registered M/D decoder, with no slew
  projection. The absence of a slew projection is a preregistered validity
  risk, not a repair opportunity.

Historical normalized reward semantics are frozen from the current V4 source,
not from the old claim prose. For observation row
`o_i=[P_es/2, dω_i(rad/s)/3, ..., neighbour slots]`, define

```
dω_i(Hz) = 3 o_i[1] / (2π)
dω_j^c(Hz) = 3 o_i[3+k] / (2π)
ωbar_i = (dω_i + Σ_j η_ij dω_j^c) / (1 + Σ_j η_ij)
r_f,i = -(dω_i-ωbar_i)^2 - Σ_j η_ij(dω_j^c-ωbar_i)^2
r_abs,i = -(dω_i)^2
a_H = mean_i(ΔM_i) / max(600, |-200|) = mean_i(ΔM_i)/600
a_D = mean_i(ΔD_i) / max(600, |-200|) = mean_i(ΔD_i)/600
r_H = -(a_H)^2
r_D = -(a_D)^2
r_i = 100 r_f,i + 50 r_abs,i + 0.0056 r_H + 0.0056 r_D
```

`η=0` for the no-message arm and `η=1` for registered neighbours in the
message arm. The reward is rebuilt from the observation row and executed
physical increments, matching `V4Config.paper_faithful()` plus
`action_penalty_mode="normalized"`. This explicitly preserves the historical
implemented adapter: it includes the repository's `phi_abs=50` term and the
R18-rescaled `phi_h=phi_d=0.0056`; it is not mislabeled as literal Eq.14.

All other contract fields are inherited from R428: eight profiles, 240 learned
evaluation records plus 24 deterministic records, frozen development scenario
order, direct bounded delta-M/delta-D decoder, physical endpoints, guards,
missing-run rules, and no reuse of R428 outcomes as R429 measurements.

## Methodology

The new runner is a thin adapter over the frozen R428 harness. It rebinds only
the round paths, the two SAC learner factories, their reward reconstruction,
the real-learner semantic probe, and machine labels. It exposes separate
training and evaluation shard identifiers to the existing shared shard driver,
so both phases use the measured process budget. Targeted tests pin the learner
class, twin-Q endpoint, reward coefficients/denominators, message mask, matched
budget, and shard grammar before any physical capacity task.

## Pre-registered decision tree

1. Any missing/corrupt run, non-finite learner diagnostic, exhausted
   preregistered crash quota, evaluation TDS failure, or incomplete record bank
   => `CANARY-INVALID`; preserve artifacts, no retry or repair in R429.
2. Otherwise run the frozen classifier. If any adapted-SAC arm passes every
   physical guard or the matched classification flips, report that endpoint
   without promotion to a universal SAC/MARL claim.
3. If both adapted-SAC arms remain invalid/fail, report the bounded endpoint:
   normalized action-cost adaptation and twin-Q SAC did not make this frozen
   bundle valid. Do not infer that all SAC variants fail.
4. Compare only same-contract R429 vs R428 and R425 endpoints/guard
   distributions. CLM-0045/0048/0059 remain historical context, not pooled
   numerical evidence.
5. No rate projection, reward retuning, alpha tuning, architecture change,
   fresh seed, bank retry, or follow-on training is authorized by any outcome.
6. Because this changes the training reward family, closeout must report both
   the project multi-axis readout and the paper `cum_rf` readout when available;
   disagreement is reported rather than collapsed. No `cum_rf` threshold is
   used to release or retry the canary.

The semantic rehearsal must verify on the real learner: twin-Q minimum target,
actor loss direction, alpha-loss direction, target soft update, reward
non-positivity, the normalized denominators, `phi_abs` presence, and the
masked-message identity.

## Capacity and execution card

- Stage: frozen formal evidence after representative capacity and formal-entry
  rehearsal.
- Independent jobs: nine training shards (three arms x three seeds), then ten
  evaluation shards (nine learned arm-seeds plus one deterministic reference),
  then serial classification and archive closeout.
- Capacity ladder: representative adapted-SAC physical tasks, 32 completions
  per rung at 1/2/4/8/12/16 workers; native numerical threads fixed to one.
- Memory rule: total concurrent training-worker RSS + 3 GiB OS floor <= WSL
  MemTotal; other_reserved_processes=0. R428's same-day 16-worker/17-process
  result is only the prior, not R429 capacity evidence.
- Frozen expected budget if the new ladder confirms it:
  `host_process_budget: 17`, `wsl_python_processes: 17`,
  `native_threads_per_process: 1`, `other_reserved_processes: 0`.
  If the ladder selects another rung, update these four pre-seal values, rerun
  preflight, then seal; never resize an active attempt.
- Training ETA basis: user-provided about 2.2 h per run; at nine ready shards
  and a selected rung >=9, `ceil(9/c)=1` training wave plus launch/tail
  overhead. Evaluation basis: 264 records and the registered about 12 s serial
  record anchor; at ten arm-seed shards and c>=10, one shard wave. Recalibrate
  only from operational completion timing, never intermediate outcomes.
- Monitoring: process count, completed shard count, terminal artifacts,
  memory/disk safety, and engineering failures only. Scientific outcomes stay
  unread until all formal evaluation records exist and classification begins.

Execution readiness is `MEASURE-FIRST` until the R429 ladder, targeted tests,
preflight, and same-entry rehearsal pass. It becomes `RUN-READY` only when the
measured process budget is frozen in this plan and seal.

## Formal launch contract

- formal_entry: training through
  `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r429_adapted_sac.py --shards tmp/andes/r429_train_shards.json --workers <selected> --round R429`, then the same driver with `r429_eval_shards.json`, then
  `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r429_adapted_sac.py classify`.
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r429_adapted_sac.py rehearse`.
- rehearsal_scope: same-pre-attempt-path; authority/source/parent/runtime/output checks, one physical step per arm, full real batch, real SAC update, objective-semantics probe, save/load roundtrip; creates no formal attempt or result.
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, adapted_sac_semantics_probe
- capacity_evidence: memory/rounds/R429/capacity_evidence_v3.json
- host_process_budget: 17
- wsl_python_processes: 17
- native_threads_per_process: 1
- other_reserved_processes: 0

## Asset protection and scope limits

- Byte-unchanged: `sac.py`, `sac_base.py`, `sac_ctde.py`, V4 environment,
  R419/R425/R428 runners, classifiers, results, checkpoints, and all historical
  claims/feeds.
- New only: R429 adapter runner/tests, R429 plan/rehearsal/capacity/seal,
  create-only R429 results, feed/claim/verdict and line evidence pointer at
  closeout.
- `sac_ctde.py` is source context only; R429 uses the per-agent `SACAgent`
  endpoint registered by CLM-0048, not a fourth CTDE arm.
- No manuscript prose is edited in this round. Any allowed manuscript use is a
  later evidence-audit decision after full closeout and before the final-paper
  freeze.

## Gate calibration target

At closeout record whether the capacity ladder, objective-semantics probe, and
post-seal abort rule were too hard, too soft, or right. No gate is relaxed
inside the attempt.

## Cross-references

- Historical design inputs: CLM-0045, CLM-0048, CLM-0059.
- Same-contract endpoints: R428/CLM-1305 and R425/CLM-1290.
- Workflow authority: `paper/yang_md_decoupling_marl/LINE.md`, the owner order
  in this task, `CLAUDE.md`, and `skills/kundur-round/SKILL.md`.
