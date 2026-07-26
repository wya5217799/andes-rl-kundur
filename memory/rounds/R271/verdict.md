# R271 verdict — current M/D-only proxy requires model/actuator correction

**Date**: 2026-07-25
**Status**: CLOSED-POSITIVE
**Type**: source/equilibrium and immutable-trace actuator-authority audit
**Claim**: CLM-0565

## TL;DR

R271 ran no new simulation and no training.  It audited the exact repository
action path, the installed ANDES 2.0.0 GENCLS equations, and immutable R270
trajectories.  All 10 source/equilibrium checks and all 6 trace checks passed.
The registered verdict is **MODEL-CORRECTION-REQUIRED**: current M/D control
has useful fast transient and differential safety authority, but the model
lacks the active-power, energy, or secondary state needed for a credible
sustained common-frequency-restoration claim.

## Frozen audit

- Repository paths: current `base_env.py` and `andes_vsg_env_v4.py`.
- Simulator paths: the active WSL installation at
  `/home/wya/andes_venv`, ANDES version `2.0.0`.
- Trajectories: immutable R270 droop and fixed-library traces only.
- Windows: first 15 samples for active action and final 25 samples (5 s) for
  terminal behaviour.
- Materiality: the R270 prospective 2% threshold, unchanged after results.
- Budget: zero new ANDES trajectories, zero training runs, and no environment,
  controller, reward, manuscript, or figure changes.

The audit script SHA-256 is
`3ddcb77a56eb19272443a430ac2bd37db2106b24ce34c376e8bfe7ea8ec8fa5c`.
The R270 input-summary SHA-256 is
`3d1ba1405db1cd899ee71489fa3f90496c8748d428c8f79e813c674955e09764`.
The generated R271 JSON SHA-256 is
`f87c4ffe81cafdc05c4d53487d7ee354344e2d60731cb209baa58873276e2df4`.

## Source and equilibrium result

All 10 registered checks passed:

1. The environment action is only normalized delta-M and delta-D.
2. `step()` writes only live `GENCLS.M` and `GENCLS.D`.
3. Installed ANDES uses
   `M*domega/dt = tm - te - D*(omega-1)`.
4. At equilibrium M disappears from the balance equation.
5. Finite D is proportional speed-error torque, not integral restoration.
6. Each VSG is a PV+GENCLS proxy.
7. The fallback mechanical-power setpoint is fixed `tm0`.
8. Governors attach to the original GENROU machines, not the VSG GENCLS units.
9. The active V4 path has no storage-energy, SOC, or headroom state.
10. `P_es` is measured electrical output, not an independent power command.

The equilibrium interpretation is therefore specific and testable:

`0 = tm - te - D*(omega-1)`.

Changing M shapes the trajectory but cannot change this equilibrium relation.
Finite D can reduce a sustained frequency error, but exact zero error under a
nonzero sustained imbalance requires a changed power setpoint or an
integral/secondary mechanism.

## Existing-trajectory result

The immutable R270 audit passed all 6 registered trace guards:

| Endpoint | Selected oracle minus droop |
|---|---:|
| full-horizon VSG-mean IAE | **-0.311271%** |
| full-horizon normalized synchronization loss | **-7.805520%** |
| full-horizon worst-bus peak | **-8.209868%** |
| full-horizon max sampled RoCoF | **-11.113147%** |
| terminal-window common absolute mean | **+0.017570%** |
| terminal common-frequency sample | **+0.011716%** |
| terminal-window differential MSE | +1.411617% |

Negative values are improvements.  The oracle's transient differential and
safety gains are material, while the full-horizon common IAE gain is only
0.31% and its terminal common metrics are marginally worse, not better.

For `common_M_pos`, M is exactly `350` during the registered 15-step active
window and exactly returns to the `200` baseline afterward.  Its early common
absolute mean improves `6.213272%` and worst-bus peak improves `11.250545%`,
but its final-5-s common absolute mean is `0.022486%` worse.  The measured VSG
electrical power changes during the transient, but the model contains no
independent commanded energy-limited power channel.

## Outcome against the pre-registered gate

| Gate | Result |
|---|---|
| source/equilibrium checks all pass | PASS — 10/10 |
| existing-trace checks all pass | PASS — 6/6 |
| R270 full-horizon IAE improvement remains below 2% | PASS — 0.311271% |
| selected terminal common-window improvement below 2% | PASS — actually 0.017570% worse |
| selected terminal common-sample improvement below 2% | PASS — actually 0.011716% worse |
| differential or safety gain at least 2% | PASS — 7.81% to 11.11% |
| scheduled common M returns to baseline | PASS — 350 to 200 |

Classification: **MODEL-CORRECTION-REQUIRED**.

## Feasibility decision

- **Research platform:** feasible.  It supports real ANDES execution,
  source-hashed provenance, immutable trajectory reuse, physical endpoints,
  prospective gates, and automated claim/question closure.
- **Original four-VSG neural M/D control thesis on one Kundur topology:** not
  feasible as a strong standalone research direction on the current model.
  Another TD3/SAC/LSTM/reward/seed sweep cannot create absent sustained
  power-balance authority.
- **M/D-only joint restoration:** closed for the current implemented
  environment.  M/D remains valuable only as a fast layer for RoCoF, peaks,
  and inter-area synchronization.
- **Scientifically viable pivot:** correct the VSG/storage actuator model
  first.  Before implementation, source and freeze power rating, energy
  capacity, SOC limits, headroom, ramp/lag, and a classical
  active-power/secondary-frequency baseline.
- **Conditional future controller:** only after the corrected classical model
  demonstrates a material attainable margin should learning resume as a
  bounded multi-timescale residual: fast M/D safety shaping plus slow
  energy/power restoration.  Topology generalization and safety evidence come
  after that gate.

This conclusion is restricted to the current model, action contract, and
tested disturbance envelope.  It is not a proof that every time-varying M/D
law or every physical VSG cannot affect terminal frequency.

## Assets

- `memory/rounds/R271/plan.md`
- `scripts/audit_actuator_authority.py`
- `tests/test_actuator_authority_audit.py`
- `results/r271_actuator_authority_audit/actuator_authority_audit.json`
- `results/r271_actuator_authority_audit/actuator_authority_audit.md`
- `memory/claims/CLM-0565.md`

## Verification

- R271 preflight: clean except the informational no-concrete-baseline notice;
- focused actuator-authority tests: 8 passed;
- Ruff on the audit script and focused tests: passed;
- full Windows suite: 384 passed, 3 WSL-only skipped, 1 known xfail;
- formal WSL audit: source 10/10, trace 6/6;
- no new ANDES trajectory and no new training run.

## Questions opened (this round)

- None.  The current automatic experiment sequence stops at the model contract
  boundary; a future question requires a physically sourced actuator
  specification rather than another algorithm.

## Questions closed (this round)

- Q-0033 — closed-positive by CLM-0565.  Current M/D-only VSG proxies require
  an explicit, physically bounded active-power or secondary mechanism for a
  credible sustained common-frequency-restoration research claim.

## Questions advanced (this round, status unchanged)

- None.

## 给 PI 的话

**这轮干了啥**：没有再训练网络，也没有新增仿真。我核对了环境动作、四台 VSG 代理、WSL 里实际安装的 ANDES 方程，并重新分析 R270 已冻结轨迹的前 15 步和最后 5 秒。

**结果（一句话）**：10/10 个源码与平衡方程检查、6/6 个轨迹门槛都通过，正式结论是 **MODEL-CORRECTION-REQUIRED**——当前 M/D 能改善瞬态安全，但不足以支撑可信的持续共同频率恢复。

**关键证据**：R270 oracle 的同步损失、峰值和 RoCoF 分别改善 `7.81%`、`8.21%`、`11.11%`，但全时域 IAE 只改善 `0.31%`；最后 5 秒共同频差均值反而差 `0.0176%`。动作结束后惯量从 `350` 精确回到 `200`，而模型里没有独立功率命令、SOC、能量或 headroom 状态。

**项目判断**：平台本身可行且审计能力很好；“固定 Kundur 上让神经网络只调四台 VSG 的 J/D 来做完整调频”这条主线不可行。M/D 应保留为快瞬态/同步安全层，不应继续换 TD3、SAC、LSTM、reward 或 seed。

**以后若继续**：先从物理来源冻结有功执行器的额定功率、能量容量、SOC、headroom、ramp/lag 和经典二次调频基线；只有经典模型先证明存在足够收益空间，才值得研究“快 M/D + 慢功率”的有界 residual，再进入拓扑泛化和安全验证。

**你想插一脚就说**：当前自动实验序列已经停止，没有论文写作产出。若你允许扩大执行器模型范围，下一阶段应先做物理模型与基线规格，不是直接训练新网络。
