# R276 verdict — validated fast and slow layers are additive, not synergistic

**Date**: 2026-07-26
**Status**: CLOSED-NEGATIVE
**Type**: experiment
**Wall**: ~1 h

## TL;DR

R276 is ADDITIVE-ONLY: all 96 four-arm records were valid, but none of six
registered physical endpoints showed a material uncertainty-supported
fast/slow interaction. The slow active-power and fast-inertia layers remain a
strong classical benchmark; their joint use is useful coverage, not evidence
of novel coordination or permission to train MARL.

## Methodology

R276 completed the exact four-arm factorial comparison frozen before the
first new trajectory:

- zero support: 24 immutable R274 feasibility-screen traces;
- slow only: 24 immutable R274 droop+PI/storage traces;
- fast only: 24 new R276 traces with the exact R275 common positive-inertia
  pulse and zero requested/commanded/actual BESS active power;
- combined: 24 immutable R275 slow-plus-fast traces.

The new arm ran in three disjoint WSL shards, eight cases per shard. It reused
the exact 24-case formal bank, storage DAE, solver, 300-step/60-s horizon,
60-Hz physical endpoints, action budgets, and bootstrap contract. Analysis
ran once, after all new traces existed. The registered interaction was
`combined - slow - fast + zero`; beneficial materiality required at most -2%
of the zero-arm mean with a paired-bootstrap 95% upper bound below zero, plus
the same -2%/uncertainty gate against a per-scenario best-single oracle.

## Results

All four arms completed 24/24 cases for 300/300 steps. All reused/new hashes,
completion, exact M/D action, zero-storage fast-only, tail, no-harm, and
provenance guards passed.

| Endpoint | Interaction (% of zero) | Paired 95% interval | Combined vs best single | Joint clear |
|---|---:|---:|---:|---:|
| max RoCoF | +1.487007% | [-0.836297%, +3.743806%] | -0.943555% | no |
| worst-bus peak | +0.510035% | [-1.202768%, +2.169217%] | -8.414678% | no |
| synchronization loss | +0.836112% | [-0.472529%, +2.103521%] | -0.285845% | no |
| first-3-s inter-area IAE | -0.152053% | [-0.495228%, +0.135646%] | -0.474216% | no |
| full-horizon VSG-mean IAE | +0.652918% | [+0.577349%, +0.722596%] | -0.203227% | no |
| final-window common error | +0.120171% | [+0.095919%, +0.141975%] | +0.528270% | no |

The combined arm clearly beat the per-scenario best single layer on peak
(-8.414678%, 95% interval [-11.301515%, -5.383886%]) and very slightly on
full-horizon IAE (-0.203227%, [-0.242306%, -0.160867%]). Neither was
non-additive: their interaction points were positive. No endpoint reached the
registered beneficial -2% interaction threshold.

## Interpretation

R274 and R275 remain valid positive mechanism results. Slow active power and
fast inertia solve different portions of the response, so using both is
better than choosing only one in some endpoints. R276 shows that this benefit
is explained by additive coverage; there is no measured synergy to attribute
to a coordination mechanism.

Therefore:

1. retain the transparent slow droop+PI/storage plus common-inertia pulse as
   the strongest classical reference;
2. remove “non-additive fast/slow coordination” as a novelty claim;
3. keep Q-0038 blocked;
4. before any neural training, run Q-0040 as an optimistic upper-bound audit
   of disturbance-adaptive zero-sum inertia allocation.

## Assets and provenance

- `memory/rounds/R276/plan.md`
- `memory/rounds/R276/formal_seal.json`
- `results/r276_fast_slow_factorial/formal_traces/`
- `results/r276_fast_slow_factorial/fast_slow_factorial_summary.json`
- `results/r276_fast_slow_factorial/fast_slow_factorial_summary.md`
- `results/r276_fast_slow_factorial/provenance.json`
- `results/r276_fast_slow_factorial/logs/`
- `src/andes_rl_kundur/evaluation/fast_slow_factorial.py`
- `scripts/eval_fast_slow_factorial.py`
- `tests/test_fast_slow_factorial.py`
- `memory/claims/CLM-0590.md`

The summary SHA-256 is
`49d2b84c7b70c3a17c38e11a915b6e89a89f93b3876f57cdd897b5e7370d088d`;
the provenance SHA-256 is
`0a834d600526c7147b12fe53ca9957181bfa445e72f62409b5267f72060c57f8`;
the formal-seal SHA-256 is
`94501f330d250928603f6cfee47040f2f86c4f0586adf7f7a06cba173a9513c8`.

## Verification

- New formal trajectories: 24/24 complete, 300/300 steps, three shard stderr
  logs empty.
- Reused R274/R275 traces: 72/72 verified by immutable hash.
- Four arms: 96/96 records complete with no TDS failure.
- Fast-only BESS request/command/actual power and energy: exactly zero; SOC
  stayed exactly 0.5.
- Fast-only action audits: 24/24 pass every exact amplitude, duration, slew,
  L1, TV, M/D range, and saturation check.
- Completion, physical, tail, storage, action, and provenance guards: pass.
- Focused Windows tests before formal execution: 12 passed, 2 skipped.
- Full Windows suite before closure: 422 passed, 8 skipped, 1 expected xfail.
- Focused WSL real-ANDES/V4 suite before closure: 17 passed.
- Ruff, preflight, dual-metric lint, validation, and rendering are rerun at
  closure.

## Questions opened (this round)

- Q-0040 — run an optimistic outcome-seeing oracle over a frozen zero-sum
  inertia basis around the strong R274+R275 classical reference. Only a
  material guarded differential margin may authorize Q-0038 training.

## Questions closed (this round)

- Q-0039 — closed-negative by CLM-0590 with the registered ADDITIVE-ONLY
  classification.

## Questions advanced (this round, status unchanged)

- Q-0038 — remains open but blocked. R276 supplies no non-additive
  coordination justification; Q-0040 must first establish a learnable
  differential-inertia margin.

## 给 PI 的话

**这轮干了啥**：我没有训练 AI，而是把零控制、慢有功、快惯量、快慢联合四种情况放进同一个 24 场景配对实验。已有 72 条轨迹全部按哈希复用，只新增 24 条快层单独运行，并用 3 个 ANDES 进程并行完成。

**结果（一句话）**：结论是 **ADDITIVE-ONLY**；96/96 条记录全部有效，但六个物理指标没有一个通过“至少 2% 且置信区间明确为负”的非加性协同门槛。

**意外**：快慢联合确实把最坏母线峰值进一步降低了 8.41%，但因子分解显示这来自两个有效经典层的加法覆盖，不是协调产生的新收益。也就是说，“两个层都值得保留”和“需要 MARL 协调”是两件不同的事。

**我默认下一步做**：先不并行训练多个模型。下一轮给零和惯量分配一个故意占便宜、能看完整结果的动作库 oracle，并用 8 路 ANDES 并行测试它相对当前经典基线还能挖出多少差模收益；连这个上界都赢不了，就直接判定当前固定拓扑不需要 RL。

**你想插一脚就说**：如果你希望提前停止 MARL 路线，现在就可以停；否则我按这个最省训练算力的上界实验继续，只有确认存在可学习余量后才启动多种子并行训练。
