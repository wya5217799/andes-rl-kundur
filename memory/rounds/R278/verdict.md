# R278 verdict — shared hard-zero-sum MARL does not clear both pilot endpoints

**Status**: CLOSED-NEGATIVE — `PILOT-NO-GO`
**Claim**: CLM-0600
**Question**: Q-0038 → `NO-ADAPTIVE-MARL-VALUE`

## TL;DR

Seed 49 safely improved synchronization loss by 13.96%, but the 7.48%
first-3-s inter-area IAE improvement did not have a wholly favorable paired
95% interval. The prospectively frozen two-endpoint pilot gate therefore
closes `PILOT-NO-GO`; no three-seed or fresh-bank continuation is authorized.

## Methodology

- Trained exactly the frozen seed-49 memoryless parameter-shared TD3:
  300 episodes, 4,500 real-ANDES environment steps, one shared actor and one
  centralized twin critic.
- The learned action was one bounded, slew-limited scalar on
  `[+1,+1,-1,-1]`; it could redistribute inertia between the two areas but
  could not change total inertia, damping, slow active-power support, or the
  frozen R275 common-inertia pulse.
- Evaluated the frozen checkpoint for the full 60 s on all 24 viewed R277-bank
  cases against the immutable R275 combined fast/slow baseline.
- Applied the prospectively frozen paired-bootstrap co-primary gates and all
  completion, physical, action, storage, energy, safety, and CVaR90 guards.

## Measured result

| Endpoint | Reference | Policy | Relative change | Paired-bootstrap 95% interval | Gate |
|---|---:|---:|---:|---:|---|
| Normalized synchronization loss | 3.007308e-05 | 2.587492e-05 | -13.959867% | [-20.450354%, -4.706778%] | PASS |
| First-3-s inter-area IAE | 0.059127155 | 0.054705006 | -7.479048% | [-14.673387%, +0.592481%] | FAIL |
| RoCoF | — | — | -12.116287% | [-16.360010%, -7.503867%] | PASS |
| Worst-bus peak | — | — | -4.538934% | [-7.507329%, -1.469048%] | PASS |
| Full-horizon VSG-mean IAE | — | — | +0.053172% | [+0.029236%, +0.077141%] | PASS |
| Final-window common error | — | — | -0.137058% | [-0.198781%, -0.075411%] | PASS |

All 24 candidate trajectories completed 300/300 steps. Maximum command and
actual storage power remained below 0.314 pu, SOC stayed within
`[0.486074, 0.511454]`, and there were no saturation reasons or constraint
violations. All frozen action, energy, completion, slow/common, safety, and
CVaR90 guards passed.

## Analysis-only numerical repair

The first immutable analysis was `INVALID` only because it demanded a physical
zero-sum residual below `1e-8` after float32 decoding at a physical inertia
scale of 500. One float32 ULP there is `3.051758e-05`; the largest observed sum
residual was `4.577637e-05`.

The audit tolerance was repaired prospectively and transparently to four ULP,
`1.220703e-04`. No trajectory, training setting, checkpoint, bootstrap sample,
metric, decision threshold, or gate changed. The repaired classification is
therefore a valid `PILOT-NO-GO`, not a post-hoc performance rescue.

## Interpretation

The simplest constrained MARL controller contains a real signal: synchronization,
RoCoF, peak, and the point estimate of early inter-area motion all improve
without weakening the validated slow layer. But its first-3-s inter-area
benefit is not sufficiently stable across the 24 cases to clear the frozen
uncertainty gate. The result does not justify claiming reliable incremental
MARL value above the strong R274+R275 classical controller.

Per the registered stop rule, R278 ends here. Do not run the planned three
seeds or fresh formal bank. Do not retry HAWE, select a lucky seed, weaken the
baseline, or sweep reward, architecture, observation, action amplitude, or
thresholds to turn this negative result positive.

## Questions opened

- None.

## Questions closed

- Q-0038 — closed negative as `NO-ADAPTIVE-MARL-VALUE` by CLM-0600.

## Questions advanced

- None. The ICEMS manuscript decision now depends on honest framing of the
  completed R274–R278 evidence, not on another controller-training round.

## Verification

- Frozen checkpoint:
  `724f9edde39d5b68c913e91283e62c3fee6030af2fc9b8ccfd8770b5c7654ced`
- Pilot seal:
  `ef354927d1235614e0708f321b12bb4a1137b8dc18740bec3f11e37c085353d2`
- Original immutable summary:
  `d0abf23e9d8fb6b69f98970272ed2a476b64f501b4270e0a3a4dc7097230e056`
- Analysis repair:
  `a1ece00f464b7b27ee6f10711942c48e8e44e09a286c6c356553440f9b16332b`

## 给 PI 的话

**这一轮干了什么**：我把最简单、最受约束的 MARL 真正训练并测完了：一个共享、无记忆的 TD3，只能在两区域之间做总和为零的惯量重分配。训练 300 回合，随后与最强经典控制器逐场景比较了 24 条完整 60 秒轨迹。

**结果（一句话）**：结论是 **PILOT-NO-GO**——同步损失改善 13.96%，统计区间完全小于零；但前三秒区域间振荡积分虽然改善 7.48%，区间上界仍为 +0.59%，所以没有同时通过两个预先规定的主门槛。

**意外**：这个方法不是“完全没用”。它让 RoCoF、峰值、同步损失都明显变好，而且功率、SOC、能量、尾部风险全部安全；真正没过的是跨场景不确定性。第一次分析里的“物理零和失败”也只是 float32 在 500 量级的一格舍入误差，不是控制器偷改了总惯量；修复审计后结论仍然是 no-go。

**我默认下一步做**：停止继续训练这个 MARL，不跑三个种子，不换奖励、网络、幅度或弱基线补救，也不把 HAWE 捡回来。R274–R278 的实验链已经足够回答研究问题；LaTeX 骨架先停写，等我们决定用“诚实的受约束 MARL 评估”还是更偏物理解耦的叙事后再写全文。

**你想插一脚就说**：如果你坚持标题完全不改，也可以写，但正文必须明确“同步改善成立、区域间收益尚不确定”，不能包装成全面胜出。如果你更看重录用概率，我们下一次只讨论论文叙事和标题边界，不再偷偷加实验救结果。
