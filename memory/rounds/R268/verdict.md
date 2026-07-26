# R268 verdict — corrected bounded residual is executable but misses the physical mechanism gate

**Date**: 2026-07-25
**Status**: CLOSED-NEGATIVE
**Type**: correctness-first real-ANDES feasibility pilot
**Claim**: CLM-0540 (superseded by CLM-0550 in R269)

## TL;DR

R268 implemented one training/deployment-identical bounded residual contract,
trained the pre-registered memoryless TD3 seed, and completed all 16 real-ANDES
pilot trajectories.  The implementation and every safety/action/completion
guard passed, but residual versus droop worsened both co-primary means:
VSG-mean IAE by `+0.094756%` and normalized synchronization loss by
`+0.076495%`.  The prospective result is therefore **NO-GO**; the exact
TD3/k10/beta0.10 contract closes and the conditional multi-seed/sealed-bank
stage is not opened.

## Post-round correction

R269 verified that the immutable R268 training log has `phi_abs=50.0`, not
zero.  Therefore the numerical NO-GO in this verdict remains valid, but the
later blocker-diagnosis statements attributing it to a missing
absolute/common-mode reward term are superseded by CLM-0550.  R268 alone does
not uniquely identify reward, optimization, observation, parameterization, or
plant control authority as the cause.

## Executed contract

The actor output was interpreted as a normalized residual under the single
composition shared by training and evaluation:

`u_exec = clip(u_droop(k=10) + 0.10 * u_residual, -1, 1)`.

- algorithm: memoryless TD3;
- seed: 49;
- training: 75 episodes, 3,750 steps, hidden layers `64,64,64,64`;
- V4 paper-faithful dynamics and normalized-action reward;
- reference-feasible pilot: `PQ_0`, `PQ_1`, `PQ_Bus14`, and `PQ_Bus15`,
  each at `-1.5` and `+1.5`;
- controllers: droop k10 and residual TD3 seed 49;
- evaluation: 150 steps per trajectory, cyclic controller ordering, environment
  seed 42, real ANDES in WSL;
- evidence level: development feasibility pilot only; no interval-qualified or
  population claim.

The controller contract SHA-256 is
`bfc2acec164db868c885876b8905e0d6a4585adb92213f2ec202c789cf0a2471`.
The four final checkpoint hashes and all evaluation-source hashes are embedded
in `pilot_summary.json`.  Its SHA-256 is
`928cc43858b3edfaa07fdc8c3dd174bbb03858fc5dc907386513b4726b3cfe78`.

## Training and reload evidence

- The real-ANDES wrapper smoke completed 50/50 steps with zero TDS failure.
- Formal training completed 75/75 episodes and 3,750/3,750 steps with zero TDS
  failure in 525 seconds.
- The monitor reported critic loss decreasing from `0.005` early to `0.002`
  late.  This is a training-health observation, not a performance result.
- All four final checkpoints loaded twice and reproduced the deterministic
  residual-aware actions exactly.
- The training log SHA-256 is
  `e05c49b44334b2ad77d0d83c5dcbc4aa1691960aaa4c96d37fe7ebfb4df1fbd6`.

## Pilot results

Both controllers completed and settled in every scenario:

| Controller | Complete | Fail/incomplete | Settled |
|---|---:|---:|---:|
| droop k10 | 8/8 | 0/8 | 8/8 |
| residual TD3 s49 beta0.10 | 8/8 | 0/8 | 8/8 |

Residual minus droop mean effects (lower is better for every row):

| Endpoint | Droop mean | Residual mean | Effect |
|---|---:|---:|---:|
| VSG-mean IAE (Hz s) | 0.939839673 | 0.940730228 | **+0.094756%** |
| normalized synchronization loss (Hz²) | 1.370730e-05 | 1.371779e-05 | **+0.076495%** |
| worst-bus peak (Hz) | 0.069168148 | 0.068688917 | -0.692850% |
| max sampled RoCoF (Hz/s) | 0.105108552 | 0.106146738 | +0.987727% |
| action L1 (agent s) | 16.276191965 | 16.653151021 | +2.316015% |
| action total variation | 2.275494856 | 2.286667047 | +0.490979% |
| action saturation fraction | 0.001666667 | 0 | -100.000000% |

The co-primary failure is not a single-scenario artifact.  In the eight paired
cases, residual improved VSG-mean IAE in only 2/8 and normalized
synchronization loss in only 3/8.  Its per-scenario synchronization-only
diagnostic reward was higher than droop in 3/8 and lower in 5/8.

## Outcome against the pre-registered gate

| Gate | Result |
|---|---|
| all 16 traces complete | PASS |
| both co-primary means improve | **FAIL** |
| residual failure not higher | PASS |
| settling success not lower | PASS |
| safety mean within +5% | PASS |
| safety worst within +5% | PASS |
| action-TV mean within +25% | PASS |
| action-TV worst within +25% | PASS |
| saturation not higher | PASS |
| deterministic checkpoint reload exact | PASS |

Classification: **NO-GO**.

Per the subtractive gate, seeds 50 and 51 were not trained and no new sealed
bank was generated.  Those were conditional experiments authorized only by a
GO; not running them preserves the prospective contract.

## Blocker diagnosis

The evidence rules out several engineering explanations:

1. **Not reference infeasibility.**  All 16 trajectories completed, neither
   controller failed, and both settled in every case.
2. **Not training/deployment interface drift.**  Training and evaluation used
   the same pure composer; source and contract hashes matched; checkpoint
   reload was exact.
3. **No hard-bound pressure was observed.**  Across residual traces, mean
   residual L-infinity magnitude was about `0.164` to `0.184`, the maximum was
   `0.358765`, and executed-action clipping was zero.  This does not prove that
   beta=0.10 is optimal, but it gives no evidence that actor saturation caused
   the failure.
4. **The strongest supported blocker is objective validity.**  The frozen V4
   configuration has `PHI_ABS=0`, so its learning reward penalizes
   differential synchronization but contains no absolute/common-mode
   restoration term, while the pilot requires VSG-mean IAE as a co-primary
   endpoint.  Its inertia/damping penalties also apply to executed action
   averages rather than specifically to residual magnitude and variation.
5. **The learned correction is largely a small per-agent bias.**  Reconstructing
   the unclipped raw residual from executed actions and the previous local
   frequency observation gives aggregate per-agent mean inertia residuals
   `[-0.0933, -0.2064, +0.0984, +0.1519]` and damping residuals
   `[+0.2291, -0.1217, -0.0404, -0.1388]`.  The opposing signs mostly cancel
   in the fleet average but do not improve the two required physical modes.

The pilot cannot uniquely separate reward mismatch from single-seed
optimization limitations.  It can establish that spending two more seeds on
the unchanged objective would not answer the registered mechanism question.
Any second training attempt must first repair and test the physical objective,
not change algorithm, seed, horizon, or residual scale opportunistically.

## Feasibility interpretation

1. **The research platform is feasible.**  It now supports real-ANDES residual
   training, an identical deployment path, deterministic checkpoint reload,
   immutable trajectories, physical 60-Hz endpoints, completion/failure
   accounting, and prospective kill gates.
2. **The exact current controller thesis is not feasible as a positive
   result.**  Memoryless TD3/k10/beta0.10 under the frozen V4 reward did not
   beat droop on either required mean endpoint.
3. **The broader residual direction is not refuted.**  This is one seed and a
   development bank, and the reward does not encode one of its own co-primary
   endpoints.  The justified pivot is objective-aligned residual control,
   followed only then by reproducibility, topology, and safety tests.
4. **The original fixed-Kundur “try more AI algorithms” direction should
   stop.**  Another architecture sweep would neither repair objective validity
   nor produce a defensible system-level contribution.
5. **No publication-level claim is available.**  There is no corrected
   multi-seed benefit, sealed residual replication, unseen-topology evidence,
   stability certificate, or cross-simulator result.

## Assets

- `memory/rounds/R268/plan.md`
- `memory/rounds/R268/smoke.stdout.log`
- `memory/rounds/R268/train_s49.stdout.log`
- `memory/rounds/R268/eval_pilot.stdout.log`
- `results/r268_residual_td3_s49/controller_contract.json`
- `results/r268_residual_td3_s49/training_log.json`
- `results/r268_residual_td3_s49/agent_0_final.pt` through
  `agent_3_final.pt`
- `results/r268_residual_pilot_eval/traces/`
- `results/r268_residual_pilot_eval/pilot_summary.json`
- `results/r268_residual_pilot_eval/pilot_summary.md`
- `src/andes_rl_kundur/env/andes/residual_adapter.py`
- `src/andes_rl_kundur/evaluation/hybrid.py`
- `scripts/eval_bounded_residual_pilot.py`
- `memory/claims/CLM-0540.md`

## Verification

- residual-focused tests: 44 passed;
- full Windows suite before formal training: 354 passed, 3 skipped, one
  expected xfail;
- real-ANDES residual-wrapper smoke: complete, zero TDS failures;
- formal training: 75/75 episodes, zero TDS failures;
- formal pilot: 16/16 complete trajectories;
- round preflight before launch: clean apart from an informational
  no-concrete-baseline notice;
- WSL Ruff was unavailable and was not a launch blocker; tests and source-hash
  checks passed.

## Questions opened (this round)

- Q-0031 — before any second residual training run, test an objective-aligned
  physical reward/interface with explicit common-mode, differential-mode, and
  residual-specific effort/variation semantics.

## Questions closed (this round)

- Q-0030 — closed-negative by CLM-0540.  The implementation was correct and
  executable, but the exact memoryless TD3/k10/beta0.10 contract missed both
  predeclared physical mean directions.

## Questions advanced (this round, status unchanged)

- None.

## 给 PI 的话

**这轮干了啥**：把训练和部署真正统一成 `droop + 0.10×神经网络残差`，先跑真实 ANDES smoke，再训练固定 seed 49 的 75 个 episode，最后在提前定义的 8 个可行扰动上完成 droop/残差共 16 条轨迹；没有扫参数，也没有碰论文写作。

**结果（一句话）**：平台和安全/动作门槛全通过，但核心物理门槛失败——残差相对 droop 的平均 IAE 差 `0.0948%`、同步损失差 `0.0765%`，所以严格判 **NO-GO**，不再追加 seed 50/51 或 sealed bank。

**意外**：这不是 ANDES 崩溃或动作饱和；16/16 都完成、残差最大只有 `0.359`、执行裁剪为零。更像根本的目标错位：训练奖励把绝对/共模频差权重设为零，却要求 IAE 必须改善，学出的主要是互相抵消的小偏置。

**我默认下一步做**：关闭这个 TD3/k10/beta0.10 合同，也停止固定 Kundur 上继续换算法；下一轮先只修并验证目标——用物理 60-Hz 的共模/差模损失，加 residual 自身的幅值和变化代价，通过离线因果/排序检查后才允许第二次训练。

**你想插一脚就说**：你可以直接要求整个 residual 方向停止，或指定更看重频率恢复、同步、安全中的哪一个；否则我会保持“先目标有效性、后多 seed、再拓扑与稳定性”的顺序。
