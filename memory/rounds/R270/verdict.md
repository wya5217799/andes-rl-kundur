# R270 verdict — M/D has transient-shaping value but no material joint restoration margin

**Date**: 2026-07-25
**Status**: CLOSED-NEGATIVE
**Type**: controller-agnostic real-ANDES attainability diagnosis
**Claims**: CLM-0555, CLM-0560

## TL;DR

R270 ran exactly 64 pre-registered real-ANDES trajectories spanning both signs
of common/inter-area inertia/damping early-transient residuals on the eight
R268 feasible disturbances.  A disturbance-informed, outcome-seeing library
oracle selected a safe non-droop inertia schedule in 7/8 scenarios and improved
normalized synchronization loss by `7.805520%`, worst-bus peak by `8.209868%`,
and max sampled RoCoF by `11.113147%`.  VSG-mean IAE improved only
`0.311271%`, far below the pre-registered 2% joint materiality threshold, so
the verdict is **NO-MATERIAL-MARGIN** for the current M/D-only control problem.

## Frozen experiment

- Scenarios: the exact eight R268 reference-feasible disturbances, four load
  locations at `-1.5` and `+1.5`.
- Baseline: immutable R268 `droop_k10` traces, verified by per-file SHA-256.
- Candidate library: both signs of common M, common D, inter-area M, and
  inter-area D, following `AREA_OF_AGENT=[1,1,2,2]`.
- Candidate action: `clip(droop + 0.25*basis, -1, 1)` for exactly the first
  15 steps, then pure droop.
- Budget: `8 scenarios × 8 candidates = 64` new trajectories; no combination,
  amplitude, duration, adaptive optimizer, training, or second bank.
- Environment: V4 paper-faithful, seed 42, 150 steps, real ANDES in WSL.
- Oracle: per scenario, choose the minimum common+differential physical score
  among candidates that are no worse on both co-primary endpoints and satisfy
  completion, settling, 5% safety, 25% action, and saturation guards;
  otherwise choose droop.
- Interpretation: optimistic upper selection over this fixed library, not a
  deployable controller and not population evidence.

The provenance SHA-256 is
`8f498ccb4c7a534bcc968998b791baa0209deaa5c64435eb6775c52f8a285ed3`.
The final summary SHA-256 is
`3d1ba1405db1cd899ee71489fa3f90496c8748d428c8f79e813c674955e09764`.

## Completion and selection

All 64 candidate trajectories completed 150/150 steps with zero TDS failure.
All eight selected trajectories completed and settled and passed every
per-scenario safety/action eligibility guard.

| Selected schedule | Scenario count |
|---|---:|
| `common_M_pos` | 5 |
| `area_M_pos` | 1 |
| `area_M_neg` | 1 |
| droop k10 | 1 |
| every damping schedule | 0 |

The oracle selected non-droop in 7/8 scenarios.  `common_M_pos` was eligible
in 5/8 scenarios; the two selected inter-area inertia signs handled one
scenario each.  No damping candidate was eligible in any scenario.

Across the complete 64-candidate library, the most frequent ineligibility
reasons were:

- normalized synchronization loss worse than droop: 38 occurrences;
- VSG-mean IAE worse: 29;
- max sampled RoCoF more than 5% worse: 27;
- worst-bus peak more than 5% worse: 23;
- action saturation higher: 22.

These counts overlap because one candidate can fail several guards.

## Aggregate oracle result

| Endpoint | Droop mean | Library-oracle mean | Oracle minus droop |
|---|---:|---:|---:|
| VSG-mean IAE (Hz s) | 0.939839673 | 0.936914223 | **-0.311271%** |
| normalized synchronization loss (Hz²) | 1.370730e-05 | 1.263738e-05 | **-7.805520%** |
| worst-bus peak (Hz) | 0.069168148 | 0.063489535 | **-8.209868%** |
| max sampled RoCoF (Hz/s) | 0.105108552 | 0.093427685 | **-11.113147%** |
| action L1 (agent s) | 16.276191965 | 16.886358964 | +3.748831% |
| action total variation | 2.275494856 | 2.421746008 | +6.427224% |
| action saturation fraction | 0.001666667 | 0.001562500 | -6.250000% |

The historical synchronization-only `cum_rf_total` mean increased by
`+0.000111451` (less negative, better).  It remains a diagnostic rather than a
primary endpoint.

## Outcome against the pre-registered gate

| Gate | Result |
|---|---|
| exactly 64 candidate trajectories | PASS |
| baseline and source hashes match | PASS |
| all selected trajectories complete | PASS |
| all selected trajectories settle | PASS |
| all selected safety/action/saturation guards pass | PASS |
| non-droop selected in at least 4/8 | PASS — 7/8 |
| mean IAE improves at least 2% | **FAIL — 0.311271%** |
| mean synchronization loss improves at least 2% | PASS — 7.805520% |

Classification: **NO-MATERIAL-MARGIN**.

This is not a near miss on the joint gate.  Even a per-scenario oracle that
sees each full outcome, chooses separately by disturbance, and is allowed to
fall back to droop recovers only 0.31% common-mode IAE.

## Mechanism interpretation

1. **The current M/D inputs have real fast-transient authority.**  Early
   positive common inertia dominates the selected library and materially
   improves differential synchronization, peak, and RoCoF with modest action
   cost.
2. **That authority is mode-specific.**  The same optimistic selector barely
   changes VSG-mean IAE.  The project should not describe synchronization or
   RoCoF gains as frequency-restoration gains.
3. **Damping schedules did not provide a safe joint rescue.**  Every fixed
   early damping direction failed at least one co-primary, safety, or
   saturation eligibility condition on every scenario.
4. **R268's failure is now physically intelligible without a reward story.**
   Its tiny adverse co-primary effects occurred in a control problem whose
   M/D-only library exposes a large differential margin but a very small common
   restoration margin.
5. **The result is bounded.**  The eight schedules are a complete signed local
   common/inter-area M/D basis at one frozen amplitude/window, not a proof over
   all possible time functions.  The programme-level stop is justified by the
   prospective gate plus the accumulated R265/R267/R268 negatives, not by
   pretending this finite library is a mathematical impossibility theorem.

## Feasibility decision

- **Research platform:** feasible and now unusually auditable.  It can train,
  run real ANDES, preserve immutable traces, verify sources/baselines, separate
  common/differential modes, and enforce prospective stopping rules.
- **Original fixed-Kundur AI algorithm direction:** not feasible as a strong
  paper thesis.  More TD3/SAC/LSTM variants do not create common-mode control
  authority.
- **M/D-only joint restoration thesis:** closed on the current environment.
  The best deliberately optimistic fixed-library oracle missed the sole
  materiality gate by a factor of about 6.4.
- **Remaining physical opportunity:** fast inertia shaping for inter-area
  synchronization, RoCoF, and peak reduction is real.
- **Recommended scientific pivot:** first establish whether an explicit
  active-power/secondary-frequency actuator is required for common-mode
  restoration.  Only a multi-timescale architecture with separate fast
  M/D transient shaping and slow power restoration would justify returning to
  learned control, topology generalization, and safety certification.
- No manuscript, topology, stability-certificate, or cross-simulator claim is
  produced in this round.

## Assets

- `memory/rounds/R270/plan.md`
- `memory/rounds/R270/run_formal.sh`
- `memory/rounds/R270/evaluate.stdout.log`
- `memory/rounds/R270/evaluate.stderr.log`
- `src/andes_rl_kundur/evaluation/attainable_oracle.py`
- `scripts/eval_attainable_oracle.py`
- `tests/test_attainable_oracle.py`
- `results/r270_attainable_oracle_smoke/smoke_trace.json`
- `results/r270_attainable_oracle/provenance.json`
- `results/r270_attainable_oracle/traces/`
- `results/r270_attainable_oracle/attainable_oracle_summary.json`
- `results/r270_attainable_oracle/attainable_oracle_summary.md`
- `memory/claims/CLM-0555.md`
- `memory/claims/CLM-0560.md`

## Verification

- R270 preflight: clean, one informational no-concrete-baseline notice;
- focused scheduled-controller/hybrid/physical tests: 39 passed;
- Ruff on all three new R270 files: passed;
- full Windows suite before launch: 376 passed, 3 skipped, one expected xfail;
- real-ANDES 10-step smoke: complete, zero TDS failure;
- formal real-ANDES batch: 64/64 complete, zero TDS failure;
- formal runner wrote and verified source, plan, baseline, and contract hashes
  before final analysis.

## Questions opened (this round)

- Q-0033 — determine from model equations and existing trajectories whether
  material common-mode restoration requires an explicit active-power or
  secondary-frequency actuator beyond virtual M/D.

## Questions closed (this round)

- Q-0032 — closed-negative by CLM-0555.  The optimistic library oracle exposed
  material differential/safety authority but only 0.311% IAE improvement,
  failing the registered 2% joint margin.

## Questions advanced (this round, status unchanged)

- None.

## 给 PI 的话

**这轮干了啥**：不训练网络，直接给控制对象开“上帝视角”。我固定了共模/区间模 × 惯量/阻尼 × 正负方向共 8 个早期动作，在 8 个可行扰动上跑完 64 条真实 ANDES，再让 oracle 每个场景挑一个同时满足物理、安全和动作约束的最好结果。

**结果（一句话）**：oracle 在 7/8 场景都能挑到比 droop 好的惯量动作，同步损失降 `7.81%`、RoCoF 降 `11.11%`、峰值降 `8.21%`，但平均 IAE 只降 `0.31%`，没过预注册的 2%，所以是 **NO-MATERIAL-MARGIN**。

**意外**：问题不是 M/D 完全没控制力，而是控制力高度偏科——早期加惯量很会压差模振荡和瞬态风险，却几乎不负责共同频率恢复；8 个 damping 方向没有一个在任何场景通过完整 eligibility。

**我默认下一步做**：停止在当前 Kundur 上继续换 TD3/SAC/LSTM 或调 residual。先从方程和现有轨迹确认共同频率恢复是否必须增加显式 active-power/二次调频执行器；若需要，未来方向应是“快 M/D 管瞬态 + 慢功率管恢复”的多时间尺度控制，而不是单纯换神经网络。

**你想插一脚就说**：你可以选择保留“M/D 只做 RoCoF/同步安全层”这个窄方向，或允许研究加入 active-power 执行器；否则我会把当前 M/D-only 双指标 AI 主线正式视为结束。
