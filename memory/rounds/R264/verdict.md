# R264 verdict — low-cap mode gate shows a small discovery-set mechanism signal

**Date**: 2026-07-24
**Status**: CLOSED-PARTIAL
**Type**: research
**Wall**: ~8.3 min real ANDES evaluation plus implementation, audit, and regression

## TL;DR

The pre-registered common/differential-mode gate did not produce a strong
dual-metric winner. Its low-capacity setting (`alpha_cap=0.25`) did, however,
clear the pre-registered static-frontier lift threshold by a narrow margin and
improve every reported non-settling physical frequency endpoint relative to
static alpha=0.25. Q-0027 therefore closes partial, not positive: this is a
mechanism signal on the same LS1/LS2 discovery scenarios and a legacy R201
checkpoint. Q-0028 carries the exact frozen gate to a sealed disturbance bank.

## Controller and experiment

The shared gate separates differential and common frequency content from
V4's normalized local frequency observation:

`rho = std(x) / (abs(mean(x)) + std(x) + 1e-8)`

`alpha_t = alpha_cap * clip(rho / 0.05, 0, 1)`

`a_t = a_R201 + alpha_t * (a_droop_k10 - a_R201)`

The full-scale ratio (0.05), capacities `{0.25, 0.50, 1.00}`, droop gain,
checkpoint, seed, horizon, scenarios, and gates were fixed in the R264 plan
before launching ANDES. The six controller traces and two no-control traces
all completed 150/150 steps.

The evaluation used:

- Ubuntu WSL, ANDES 2.0.0, Python 3.12.3;
- frozen `results/r201_w1_hreg_tau005_s54` best checkpoint;
- droop k=10, seed 42, canonical LS1+LS2;
- legacy diagnostics on the frozen 50-Hz basis;
- physical endpoints on the detected ANDES 60-Hz basis.

## Results

Higher `geo`, less-negative `cum_rf`, and higher frontier lift are better.

| alpha cap | mean alpha LS1/LS2 | geo | cum_rf | static-frontier geo | lift | gate result |
|---:|---:|---:|---:|---:|---:|---|
| 0.25 | 0.0740 / 0.0687 | **0.355574** | -0.055514 | 0.350242 | **+0.005331** | mechanism signal |
| 0.50 | 0.1445 / 0.1331 | 0.205497 | -0.045108 | 0.237502 | -0.032005 | below frontier |
| 1.00 | 0.3781 / 0.3853 | 0.126244 | **-0.031758** | outside measured range | N/A | paper metric only |

The capacity-1 gate extends `cum_rf` beyond pure droop
(`-0.031758` versus `-0.036712`) but sacrifices most of `geo` and raises
action total variation to 41.57/45.27. It is another trade-off point, not a
dual win.

## Pre-registered gate evaluation

| Gate | Outcome |
|---|---|
| STRONG DUAL WIN: `geo>0.4152387309` and `cum_rf>-0.0367117095` | **MISS** |
| BALANCED FOLLOW-UP: `geo>=0.35` and `cum_rf>=-0.055` | **MISS**; cap 0.25 misses `cum_rf` by 0.000514 |
| MECHANISM SIGNAL: frontier lift >= 0.005 | **PASS**; cap 0.25 lift = 0.005331 |
| INVALID: failed/incomplete/provenance/test failure | **NOT met** |

Per the plan, Q-0027 closes **partial**.

## Expanded physical endpoint comparison

The most meaningful like-for-like physical comparison is the cap-0.25 gate
against R262's static alpha=0.25 controller. Both combine the same frozen R201
and droop k=10 components; only state dependence changes. Negative percentages
below are improvements (lower is better).

| 60-Hz physical endpoint | LS1 change | LS2 change |
|---|---:|---:|
| worst-bus peak absolute frequency | -2.46% | -1.25% |
| VSG-mean peak absolute frequency | -0.74% | -0.31% |
| VSG-mean IAE | -3.80% | -4.45% |
| differential dispersion RMS | -1.65% | -1.13% |
| differential dispersion ISE | -3.28% | -2.25% |
| maximum sampled RoCoF | -2.11% | -0.62% |
| terminal worst-bus error | -5.32% | -6.20% |
| settling to 0.05-Hz band | equal (4.5 s) | equal (3.3 s) |

Thus all seven non-settling frequency outcomes improved in both scenarios and
settling did not regress. The margins are small and paired on only two
discovery scenarios; they are not uncertainty-qualified generalisation
evidence.

## What R264 says about the evaluation methods

The cap-0.25 gate has better physical frequency outcomes than static
alpha=0.25, yet lower `geo` (`0.355574` versus `0.372745`). This is not merely
a coding discrepancy. One directly inspected cause is the symmetric
paper-target distance:

- LS1 legacy peak improves from 0.119397 to 0.116460 Hz, but its axis score
  falls from 0.893967 to 0.864604 because both are below the 0.13-Hz paper
  target and the smaller deviation is farther from that target.
- LS2 peak improves from 0.094862 to 0.093674 Hz, while its axis score falls
  from 0.948617 to 0.936738 for the same reason.

Other action-smoothness and late-oscillation axes also affect `geo`; R264 does
not claim all aspects of the gated response are better. It does establish that
`geo` is non-monotone with respect to basic physical improvements. The
appropriate hierarchy is therefore:

1. physical frequency, failure, constraint, cost, and tail outcomes;
2. normalized differential synchronization as a named mechanism endpoint;
3. the 11-axis `geo` score as a frozen paper-alignment diagnostic, not
   “overall control quality.”

The paper `cum_rf` remains reasonable for differential synchronization but
still cannot detect common-mode drift or high action variation. The cap-1
result demonstrates that limitation: excellent `cum_rf` coexists with poor
`geo` and very high action variation.

## Claim + falsification

**Claim**: on canonical seed-42 LS1+LS2, the pre-registered cap-0.25
mode-ratio gate produces a small state-selection mechanism signal relative to
the measured static blend frontier and improves the reported physical
frequency endpoints relative to static alpha=0.25.

**Not claimed**: corrected recurrent superiority, independent replication,
statistical significance, broad disturbance robustness, topology transfer,
stability, or publication-level algorithm superiority.

**Killshot**: a prospective paired disturbance bank that shows null/reversed
physical effects or unacceptable tail/failure/action-variation cost closes
this hand-designed gate. R264's 0.000331 margin above the mechanism threshold
is small enough that independent replication is mandatory.

**Independent verification path**: rescore the six R264 trace files, recompute
the physical endpoints from `delta_f_physical_hz`, and compare the cap-0.25
row with the immutable R262 alpha=0.25 traces. No verdict prose is required.

## Verification

| Layer | Result |
|---|---|
| Real ANDES controller traces | **6/6 complete**, 150/150 steps |
| Real ANDES no-control traces | **2/2 complete**, 150/150 steps |
| Frequency provenance | legacy control 50 Hz + physical ANDES 60 Hz explicit |
| Focused hybrid/physical/paper-path tests | **32 passed** on Windows |
| Windows full tests | **329 passed, 3 skipped, 1 expected xfail** |
| WSL full tests with real ANDES | **342 passed, 1 expected xfail** |
| Ruff on changed Python files | **all checks passed** |
| Dual-metric lint | **269 claims passed** |

The expected xfail is the known 60/50-Hz plant/contract mismatch documented
in R261 and ADR-0006.

## Assets

- `results/r264_mode_gated_residual/mode_gated_residual_summary.json`
- `src/andes_rl_kundur/evaluation/hybrid.py`
- `src/andes_rl_kundur/evaluation/physical_endpoints.py`
- `src/andes_rl_kundur/evaluation/paper_path.py`
- `scripts/eval_state_gated_hybrid.py`
- `tests/test_hybrid_evaluation.py`
- `tests/test_physical_endpoints.py`
- CLM-0520

## Questions opened (this round)

- **Q-0028** — test the frozen cap-0.25 gate on a prospectively sealed,
  paired random disturbance bank with physical and tail outcomes.

## Questions closed (this round)

- **Q-0027** — closed-partial by CLM-0520. A mechanism signal exists on
  LS1/LS2, but neither the strong-dual nor balanced gate passed.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：没有重训模型；把 R201 和 droop k=10 做成按共同/差分频率状态自动开关的残差控制器，用三个预注册容量跑了 6 条真实 ANDES 轨迹，并新增 60 Hz 物理频率端点评估。

**结果（一句话）**：严格“双指标都更优”仍未实现，但 0.25 容量刚刚抬高静态前沿 `+0.00533`，而且相对静态 0.25 在两个场景的 7 个非 settling 物理频率端点全部改善；这是部分机制信号，不是算法胜利。

**意外**：物理频率变好时 `geo` 反而从 0.37275 降到 0.35557，因为它会惩罚比论文目标更小的峰值；另一方面容量 1 的 `cum_rf` 超过纯 droop，却伴随很差的 `geo` 和巨大动作变差。这实证说明两个旧指标都不能单独代表总体控制质量。

**默认下一步**：执行 Q-0028，把门控参数冻结，在预先生成并哈希的随机扰动库上做 R201、droop、静态 0.25 和门控 0.25 的成对评估；报告区间、失败率、尾部风险和物理端点。通过后才值得做修正循环网络的多种子残差训练。

**你想插一脚就说**：你可以修改 held-out 扰动库规模或判定门槛；若不修改，我会按已写入 programme 的 Q-0028 自动继续，绝不会用 sealed bank 调门控阈值。
