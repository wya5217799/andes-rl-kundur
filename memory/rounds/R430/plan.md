---
round: R430
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-18'
closed: '2026-08-18'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R430 plan — R429 output-root successor, maximum measured parallelism

**Opened**: 2026-08-18
**Driver**: R429 was sealed then engineering-aborted before any adapted-SAC
training step because an inherited Python default argument still pointed at the
R428 result root. The owner explicitly ordered higher parallelism and a renewed
launch in the current task after that terminal artifact was reported.
**Parents**: R429 formal seal + `engineering_failure.json`; R428/CLM-1305;
R425/CLM-1290; historical design inputs CLM-0045/0048/0059.

## TL;DR

Workload: `evidence`; engineering successor with the R429 science frozen.
One code factor changes: the successor formal dispatch passes
`out_root=results/research_loop/r430_adapted_sac_successor` explicitly to the
inherited SAC training function. All learner, reward, action, bank, seed,
interaction/update, classifier, guard, scalar-anchor, evaluation, and claim
rules remain R429-identical. Nine training shards and ten evaluation shards are
each launched in a single maximum-safe parallel wave when capacity permits.

## Methodology

- Import the frozen R429 adapter and its frozen R428 parent without editing
  either source.
- Rebind only round/result/lifecycle paths to R430.
- Formal SAC dispatch calls the inherited function with explicit
  `out_root=OUT`; a rehearsal/test probe resolves every registered SAC shard to
  the R430 root and rejects R428/R429 roots.
- Scalar dispatch remains the inherited R429/R419 byte-anchor path.
- Reuse the just-completed R429 v3 capacity ladder only if a fresh host snapshot
  finds no other research processes and the inherited workload/source closure
  remains identical except for output routing. This is representative measured
  capacity, not a fixed worker guess.

## Frozen scientific contract

R429 plan and seal remain the complete scientific contract. The successor adds
only `successor_of=R429` and `explicit_sac_out_root=true` metadata. Three arms,
seeds 401/402/403, 43,200 interactions/run, eight profiles, 240 learned + 24
deterministic evaluation records, deterministic SAC evaluation, no slew
projection, no checkpoint reuse, and the frozen classifier are unchanged.

The adapted-SAC reward remains exactly:

```
dω_i = 3 o_i[1]/(2π); dω_j^c = 3 o_i[3+k]/(2π)
ωbar_i = (dω_i + Σ η_ij dω_j^c)/(1+Ση_ij)
r_f,i = -(dω_i-ωbar_i)^2 - Ση_ij(dω_j^c-ωbar_i)^2
r_abs,i = -(dω_i)^2
r_H = -(mean(ΔM)/600)^2; r_D = -(mean(ΔD)/600)^2
r_i = 100 r_f,i + 50 r_abs,i + 0.0056 r_H + 0.0056 r_D
```

`η=0` for no-message and `η=1` for registered neighbours in message. Learner
remains four independent byte-unchanged `SACAgent`s: 4x128 Gaussian+tanh actor,
per-agent twin Q/target, automatic alpha in [0.005,5], lr 3e-4, gamma 0.99,
tau 0.005, batch 256, buffer 10,000, gradient cap 1, one update per environment
step after batch warmup.

## Gate

1. Rehearsal must pass source/parent/runtime/output absence, real physical and
   learner update, `sac_semantics_probe`, save/load, and
   `successor_output_root_probe`.
2. Any missing/corrupt/non-finite shard or evaluation TDS failure =>
   `CANARY-INVALID`; preserve artifacts, no in-round retry.
3. Complete bank => frozen classifier. Report pass/fail/invalid and same-contract
   R428/R425 endpoint/guard distributions only; historical values are context.
4. Reward-family closeout carries both project multi-axis and paper `cum_rf`
   readouts when available; disagreement is not collapsed and neither releases
   a retry.
5. No tuning, rate projection, alpha/reward/architecture change, new seed,
   fresh bank, or third attempt is authorized by an outcome.

## Capacity and execution card

- Prior representative evidence: R429 v3 measured all 32 tasks valid at every
  rung 1/2/4/8/12/16 and selected 16 workers / 17 total WSL Python processes.
- R430 reuse gate: fresh no-other-process snapshot, matching logical CPU and
  memory rule, current source/runtime hashes, identical representative task.
- Expected frozen budget: `host_process_budget: 17`,
  `wsl_python_processes: 17`, `native_threads_per_process: 1`,
  `other_reserved_processes: 0`.
- Ready jobs: nine training shards then ten evaluation shards. Each phase is one
  wave at selected workers=16; no duplicate jobs are generated merely to fill
  the remaining seven/six slots.
- ETA: user-provided about 2.2 h per training run, so `ceil(9/16)=1` training
  wave plus tail; evaluation uses one ten-shard wave over the 264-record bank.
  Recalibrate from operational completion only.
- Monitor process count, completed manifest count, memory/disk, and engineering
  failures. Do not inspect intermediate scientific returns.

Execution readiness is `MEASURE-FIRST` until capacity reuse, targeted tests,
preflight, and rehearsal pass; then `RUN-READY`. Sealed concurrency is immutable.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r430_adapted_sac_successor.py --shards tmp/andes/r430_train_shards.json --workers 16 --round R430`, then the same driver with `tmp/andes/r430_eval_shards.json`, then `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r430_adapted_sac_successor.py classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r430_adapted_sac_successor.py rehearse`
- rehearsal_scope: same-pre-attempt-path; source/parent/runtime/output guards, real physical step and batch update per arm, SAC semantics, save/load, and explicit R430 output-root resolution; no formal artifact
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, sac_semantics_probe, successor_output_root_probe
- capacity_evidence: memory/rounds/R430/capacity_evidence.json
- host_process_budget: 17
- wsl_python_processes: 17
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- Byte-unchanged/read-only: R419/R425/R428/R429 source, seals, results, claims,
  feeds; `sac.py`, V4 environment, classifier, decoder, estimators.
- New only: R430 successor runner/tests, R430 lifecycle artifacts, create-only
  R430 results and closeout ledger/feed/claim.
- Dirty worktree preserved; no reset/clean/stage/commit; no manuscript prose.

## Cross-references

- R429 engineering terminal: `results/research_loop/r429_adapted_sac/engineering_failure.json`.
- R429 frozen science: `memory/rounds/R429/plan.md` and `formal_seal.json`.
- Same-contract comparison endpoints: R428/CLM-1305, R425/CLM-1290.
