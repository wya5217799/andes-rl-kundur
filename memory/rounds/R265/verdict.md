# R265 verdict — physical mean gains replicate, action variation kills the gate

**Date**: 2026-07-24
**Status**: CLOSED-NEGATIVE
**Type**: research
**Wall**: ~82 min real ANDES evaluation plus sealing, implementation, audit, and verification

## TL;DR

On a prospectively materialised and hashed 20-scenario bank, the frozen R264
cap-0.25 gate improved both pre-registered mean physical losses versus static
alpha=0.25, but increased mean action total variation by 236.67% and
descriptive CVaR90 by 448.00%. The prospective action guard therefore makes
the overall replication NEGATIVE and closes this exact hand-designed gate.

## Prospective seal

Before the first controller trajectory:

- `generate_test_scenarios(n=20, seed=20260724, include_anchors=False)`;
- 20 unique one-load disturbances, four PQ buses, 10 positive / 10 negative;
- zero exact overlap with the R58 seed-2026 random subset;
- bank SHA-256:
  `68816647eca8c0ccabe847ec883eaf59676c7afc915c09081a7851bf1e2dfae0`;
- seal-manifest SHA-256:
  `e3bec601f1e8324e4c162d608c556bbe2f1da6122090407f78d5524e05ed63bc`;
- checkpoint hashes, controller specs, co-primary endpoints, paired bootstrap,
  failure handling, CVaR90, and positive/partial/negative gates fixed in the
  plan and manifest.

The seal is repository-local prospective evidence, not a third-party
registration timestamp. SHA-256 proves byte identity, not creation time.

## Experiment

Exactly four frozen controllers ran each scenario with cyclically rotated run
order:

1. legacy deterministic R201;
2. droop k=10;
3. static R201/droop alpha=0.25;
4. R264 mode-ratio gate, `ratio_full_scale=0.05`, `alpha_cap=0.25`.

All used V4 paper-faithful defaults, env seed 42, 150 steps, real ANDES 2.0.0
in WSL. All 80/80 traces completed 150/150 steps. There were no TDS failures,
runner errors, incomplete records, non-finite endpoints, or provenance
mismatches.

Observed failure was 0/20 for every controller. The two-sided 95% exact
Clopper-Pearson interval is still [0, 16.84%], so this bank does not prove a
near-zero population failure rate. Gate/static paired completion was 20 both
successful, zero discordant, zero both failed.

## Controller dashboard

Means over the sealed bank; lower is better.

| Controller | physical mean IAE (Hz·s) | normalized sync loss (Hz²) | worst-bus peak (Hz) | max RoCoF (Hz/s) | action L1 | action TV |
|---|---:|---:|---:|---:|---:|---:|
| R201 | 0.703631 | 3.99940e-05 | 0.077730 | 0.139415 | 55.4954 | 1.7305 |
| droop k10 | 0.881179 | 1.92278e-05 | 0.071803 | 0.116995 | 15.2294 | 2.2180 |
| static 0.25 | 0.745171 | 3.16999e-05 | 0.074938 | 0.130418 | 44.8129 | 1.6355 |
| gate 0.25 | 0.712657 | 3.11095e-05 | 0.074181 | 0.129757 | 51.6245 | 5.5063 |

The four-controller context preserves the old trade-off: R201 has the best
common-mode IAE, droop has the best differential synchronization and RoCoF,
and the static blend is the smoothest controller in this bank.

## Primary gate-versus-static result

Paired percentile bootstrap: 10,000 shared scenario-row resamples, seed
2026072401. Negative effects improve a lower-is-better endpoint.

| Endpoint | ratio-of-means effect | paired 95% interval | scenario wins |
|---|---:|---:|---:|
| VSG-mean IAE | **-4.3633%** | **[-5.3689%, -3.5520%]** | 20/20 |
| normalized sync loss | **-1.8624%** | **[-2.2532%, -1.2188%]** | 9/20 |
| worst-bus peak | -1.0103% | [-1.3604%, -0.6070%] | 19/20 |
| VSG-mean peak | -0.3323% | [-0.4239%, -0.2421%] | 20/20 |
| max sampled RoCoF | -0.5066% | [-0.9091%, -0.0355%] | 14/20 |
| terminal worst-bus error | -6.5387% | [-8.1249%, -5.2883%] | 20/20 |
| action L1 | **+15.2002%** | **[+13.4618%, +16.4944%]** | 0/20 |
| action total variation | **+236.6691%** | **[+180.3890%, +299.5733%]** | 0/20 |

Both co-primary mean effects clear zero, but the synchronization result is
heterogeneous: only 9/20 scenarios improve and the median paired percentage is
+0.1442%. The predeclared estimand was the paired mean, so this does not change
the gate; it limits the interpretation to a distribution-weighted mean signal.

Action saturation was zero for both controllers. Its relative percentage is
therefore undefined; the analysis keeps the absolute difference at zero
instead of emitting infinity or deleting the endpoint.

## Tail and prospective decision gate

With n=20, empirical CVaR90 is only the mean of the worst two trajectories.
It is a descriptive guard, not precise tail inference.

| Guard | Gate vs static | Limit | Result |
|---|---:|---:|---|
| worst-bus peak CVaR90 | -1.2501% | no worse than +5% | pass |
| max RoCoF CVaR90 | -0.7405% | no worse than +5% | pass |
| worst-bus bank maximum | -1.2205% | no worse than +10% | pass |
| max RoCoF bank maximum | -0.8899% | no worse than +10% | pass |
| settling success | 20/20 vs 20/20 | not lower | pass |
| failures | 0 vs 0 | not higher | pass |
| action-TV CVaR90 | **+448.0015%** | no worse than +25% | **FAIL** |

Both co-primary physical intervals pass, but the hard action-TV guard fails by
a large margin. Per the plan, this is **NEGATIVE**, not partial. The exact
`ratio_full_scale=0.05`, `alpha_cap=0.25` gate is closed. No threshold,
capacity, checkpoint, scenario, endpoint, tail level, or decision gate was
changed after unsealing.

## Interpretation

The sealed bank upgrades R264's physical observation from two discovery
anchors to interval-qualified paired mean evidence. It simultaneously shows
why physical endpoints alone are not enough: the gate injects useful state
selection but creates unacceptable control movement.

This does not justify corrected recurrent training yet. The next programme
question is a mechanism pivot: reconstruct the per-step gate and decompose
action variation, then freeze at most one smooth dynamic gate and test it on a
new sealed bank. R265 becomes development evidence; it cannot be reused as
confirmatory evidence or as a threshold/smoothing sweep surface.

No `geo` was computed for these random scenarios. It has no paper-anchor
target there and was prospectively excluded as an overall endpoint. Legacy
normalized synchronization is retained only as a diagnostic.

## Analysis repair and independent verification

Trace production finished 80/80 before the first analysis attempt. That
attempt stopped because the relative action-saturation effect had a zero
reference denominator. No trajectory was rerun or overwritten. A read-only
representation fix retained the defined absolute zero difference and marked
the relative percentage unavailable. Producer source hashes and repaired
analysis source hashes are both stored in the final summary.

An independent raw-trace pass:

- re-hashed the bank and seal manifest;
- re-summarised all 80 physical traces and matched every stored endpoint to
  absolute tolerance 1e-15;
- regenerated the shared-index bootstrap for both co-primary endpoints and
  action TV, matching the final summary to 1e-12.

## Verification

| Layer | Result |
|---|---|
| Real ANDES traces | **80/80 complete**, 150/150 steps |
| TDS failures / runner errors | **0 / 0** |
| Frequency provenance | legacy control 50 Hz + physical ANDES 60 Hz explicit |
| Focused sealed/hybrid/physical tests | **25 passed** |
| Windows full tests | **336 passed, 3 skipped, 1 expected xfail** |
| WSL full tests with real ANDES | **349 passed, 1 expected xfail** |
| Ruff on changed Python files | **all checks passed** |
| Round preflight | **R265 clean** |
| Dual-metric lint | **270 claims passed** |
| Memory validation / render | **clean except 22 pre-existing missing-provenance warnings; STATE rendered** |

## Assets

- `memory/rounds/R265/scenario_bank.json`
- `memory/rounds/R265/scenario_bank.json.sha256`
- `memory/rounds/R265/scenario_bank.manifest.json`
- `results/r265_sealed_gate_replication/provenance.json`
- `results/r265_sealed_gate_replication/traces/`
- `results/r265_sealed_gate_replication/sealed_gate_replication_summary.json`
- `results/r265_sealed_gate_replication/sealed_gate_replication_summary.md`
- `docs/research/2026-07-24_q0028_sealed_evaluation_methodology.md`
- `src/andes_rl_kundur/evaluation/sealed_bank.py`
- `scripts/eval_sealed_gate_replication.py`
- CLM-0525

## Questions opened (this round)

- **Q-0029** — diagnose the action-variation mechanism, freeze at most one
  smooth dynamic gate, and test it on a new sealed bank.

## Questions closed (this round)

- **Q-0028** — closed-negative by CLM-0525. Physical mean gains replicate,
  but the pre-registered action-TV guard fails decisively.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：先把 20 条新随机扰动实际写盘、哈希，再让 R201、droop、静态 0.25、门控 0.25 跑完同一批 80 条真实 ANDES 轨迹；没有拿 sealed bank 调参数。

**结果（一句话）**：门控相对静态 0.25 把物理平均 IAE 降了 `4.36%`、归一化同步损失降了 `1.86%`，两个区间都过零，但动作总变差暴涨 `236.67%`、尾部涨 `448.00%`，所以按预注册规则是负结果。

**意外**：物理信号不是假的——20/20 场景的 IAE 都更好；真正杀死方案的是控制动作太抖，而且同步损失虽平均更好，逐场景只赢 9/20，说明收益不均匀。

**我默认下一步做**：不训练修正循环网络，也不在这批数据上扫阈值；先拆解门控动作变差来自 alpha 切换还是两基控制器分歧，只冻结一个平滑/滞环/限速机制，再用全新 sealed bank 检验。

**你想插一脚就说**：你可以否决 25% 动作变差护栏或指定平滑机制；若不改，我会按 Q-0029 做机制 pivot，R265 只当开发证据，不再当确认集。
